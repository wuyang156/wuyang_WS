import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.event_handlers import OnProcessExit, OnProcessStart
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_share = get_package_share_directory('wuyang_description')
    gazebo_ros_share = get_package_share_directory('gazebo_ros')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    map_yaml_path = LaunchConfiguration(
        'map',
        default=os.path.join(pkg_share, 'maps', 'laser_map', 'wheeltec_map.yaml')
    )
    nav2_param_path = LaunchConfiguration(
        'params_file',
        default=os.path.join(pkg_share, 'config', 'nav2_params.yaml')
    )
    ackermann_urdf_file = PathJoinSubstitution(
        [pkg_share, 'urdf', 'wuyang_ackermann.urdf.xacro']
    )

    # === 仿真环境 ===

    # Robot State Publisher
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{
            'robot_description': ParameterValue(
                Command(['xacro ', ackermann_urdf_file]), value_type=str
            ),
            'use_sim_time': True,
        }],
    )

    # Gazebo
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [gazebo_ros_share, '/launch', '/gazebo.launch.py']
        ),
        launch_arguments={
            'world': os.path.join(pkg_share, 'world', 'my_world')
        }.items(),
    )

    # Spawn robot
    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-topic', '/robot_description',
            '-entity', 'wuyang_car',
            '-z', '0.05',
        ],
        output='screen',
    )

    # Controller spawners
    load_joint_state_broadcaster = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster', '--ros-args', '-p', 'use_sim_time:=true'],
    )

    load_ackermann_controller = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['ackermann_controller', '--ros-args', '-p', 'use_sim_time:=true'],
    )

    # TF relay
    tf_relay_node = Node(
        package='topic_tools',
        executable='relay',
        name='tf_relay',
        arguments=['/ackermann_controller/tf_odometry', '/tf'],
    )

    # cmd_vel 转换器
    cmd_vel_converter = Node(
        package='wuyang_description',
        executable='cmd_vel_to_ackermann.py',
        name='cmd_vel_to_ackermann',
        output='screen',
    )

    # 控制器延迟加载
    spawn_exit_event = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=spawn_entity,
            on_exit=[load_joint_state_broadcaster],
        )
    )

    broadcaster_exit_event = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=load_joint_state_broadcaster,
            on_exit=[load_ackermann_controller],
        )
    )

    # === 导航 ===

    # 静态 TF: map -> odom (初始位置在地图坐标系原点)
    # 由于取消 AMCL，需要手动发布 map 到 odom 的变换
    # 小车物理放置在地图原点后，odom 从 (0,0,0) 开始累积
    static_tf_map_to_odom = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_map_to_odom',
        arguments=[
            '--x', '0.0',
            '--y', '0.0',
            '--z', '0.0',
            '--yaw', '0.0',
            '--pitch', '0.0',
            '--roll', '0.0',
            '--frame-id', 'map',
            '--child-frame-id', 'odom'
        ],
        parameters=[{'use_sim_time': True}],
    )

    # 使用 navigation_launch 而非 bringup_launch (不包含 AMCL)
    launch_navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [nav2_bringup_dir, '/launch', '/navigation_launch.py']
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'params_file': nav2_param_path,
        }.items(),
    )

    # Map Server 单独启动
    map_server_node = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'yaml_filename': map_yaml_path,
        }],
    )

    # Lifecycle Manager 用于激活 map_server
    lifecycle_manager_nav = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'autostart': True,
            'node_names': ['map_server']
        }],
    )

    # === RViz ===

    rviz2_node = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', PathJoinSubstitution([pkg_share, 'rviz2', 'nav2_only_odom.rviz'])],
        parameters=[{'use_sim_time': True}],
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument('map', default_value=map_yaml_path),
        DeclareLaunchArgument('params_file', default_value=nav2_param_path),
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        robot_state_publisher_node,
        gazebo,
        spawn_entity,
        spawn_exit_event,
        broadcaster_exit_event,
        tf_relay_node,
        cmd_vel_converter,
        static_tf_map_to_odom,
        map_server_node,
        lifecycle_manager_nav,
        launch_navigation,
        rviz2_node,
    ])
