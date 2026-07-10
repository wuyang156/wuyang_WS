from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, RegisterEventHandler, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.event_handlers import OnProcessExit, OnProcessStart
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_share = FindPackageShare('wuyang_description')
    gazebo_ros_share = FindPackageShare('gazebo_ros')
    ackermann_urdf_file = PathJoinSubstitution(
        [pkg_share, 'urdf', 'wuyang_ackermann.urdf.xacro']
    )
    map_file = PathJoinSubstitution(
        [pkg_share, 'maps', 'laser_map', 'wheeltec_map.yaml']
    )

    # 1. Robot State Publisher
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

    # 2. Gazebo
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([gazebo_ros_share, 'launch', 'gazebo.launch.py'])
        ),
        launch_arguments={
            'world': PathJoinSubstitution([pkg_share, 'world', 'wheeltec_world'])
        }.items(),
    )

    # 3. Spawn robot
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

    # 4. Controller spawners
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

    # 4.1 TF relay
    tf_relay_node = Node(
        package='topic_tools',
        executable='relay',
        name='tf_relay',
        arguments=['/ackermann_controller/tf_odometry', '/tf'],
    )

    # 4.2 cmd_vel 转换器
    cmd_vel_converter = Node(
        package='wuyang_description',
        executable='cmd_vel_to_ackermann.py',
        name='cmd_vel_to_ackermann',
        output='screen',
    )

    # 5. Map Server
    map_server_node = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[
            {'use_sim_time': True, 'yaml_filename': map_file}
        ],
    )

    # 6. AMCL
    amcl_node = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[
            PathJoinSubstitution([pkg_share, 'config', 'nav2_params.yaml']),
        ],
        remappings=[
            ('scan', '/scan'),
        ],
    )

    # 7. Nav2 lifecycle nodes
    controller_server = Node(
        package='nav2_controller',
        executable='controller_server',
        name='controller_server',
        output='screen',
        parameters=[
            PathJoinSubstitution([pkg_share, 'config', 'nav2_params.yaml']),
        ],
        remappings=[
            ('cmd_vel', '/cmd_vel_nav'),
        ],
    )

    planner_server = Node(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        output='screen',
        parameters=[
            PathJoinSubstitution([pkg_share, 'config', 'nav2_params.yaml']),
        ],
    )

    behavior_server = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        name='behavior_server',
        output='screen',
        parameters=[
            PathJoinSubstitution([pkg_share, 'config', 'nav2_params.yaml']),
        ],
    )

    bt_navigator = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        name='bt_navigator',
        output='screen',
        parameters=[
            PathJoinSubstitution([pkg_share, 'config', 'nav2_params.yaml']),
        ],
    )

    velocity_smoother = Node(
        package='nav2_velocity_smoother',
        executable='velocity_smoother',
        name='velocity_smoother',
        output='screen',
        parameters=[
            PathJoinSubstitution([pkg_share, 'config', 'nav2_params.yaml']),
        ],
        remappings=[
            ('cmd_vel', '/cmd_vel_nav'),
        ],
    )

    # 8. Lifecycle Manager（等待 map_server 启动后再激活）
    lifecycle_manager_node = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'autostart': True,
            'node_names': [
                'map_server', 'amcl', 'controller_server',
                'planner_server', 'behavior_server', 'bt_navigator',
                'velocity_smoother',
            ],
        }],
    )

    lifecycle_after_map = RegisterEventHandler(
        event_handler=OnProcessStart(
            target_action=map_server_node,
            on_start=[lifecycle_manager_node],
        )
    )

    # 9. RViz2
    rviz2_node = Node(
        package='rviz2',
        executable='rviz2',
        output='screen',
        parameters=[{'use_sim_time': True}],
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

    return LaunchDescription([
        robot_state_publisher_node,
        gazebo,
        spawn_entity,
        spawn_exit_event,
        broadcaster_exit_event,
        tf_relay_node,
        cmd_vel_converter,
        map_server_node,
        amcl_node,
        controller_server,
        planner_server,
        behavior_server,
        bt_navigator,
        velocity_smoother,
        lifecycle_after_map,
        rviz2_node,
    ])
