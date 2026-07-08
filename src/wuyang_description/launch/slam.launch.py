from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, RegisterEventHandler # type: ignore
from launch.launch_description_sources import PythonLaunchDescriptionSource # pyright: ignore[reportMissingImports]
from launch.substitutions import Command, PathJoinSubstitution # type: ignore
from launch_ros.actions import Node # pyright: ignore[reportMissingImports]
from launch_ros.substitutions import FindPackageShare
from launch.event_handlers import OnProcessExit
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_share = FindPackageShare('wuyang_description')
    gazebo_ros_share = FindPackageShare('gazebo_ros')
    ackermann_urdf_file = PathJoinSubstitution(
        [pkg_share, 'urdf', 'wuyang_ackermann.urdf.xacro']
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
            'world': PathJoinSubstitution([pkg_share, 'world', 'my_world'])
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
            '-unspawn', 'true'
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
        arguments=[
            'ackermann_controller',
            '--ros-args', '-r', '~/tf_odometry:=/tf',
            '-p', 'use_sim_time:=true'
        ],
    )

    # 5. SLAM Toolbox
    slam_toolbox_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[
            PathJoinSubstitution([pkg_share, 'config', 'slam_toolbox_mapping.yaml']),
            {'use_sim_time': True}
        ],
    )

    # 6. RViz2
    rviz2_node = Node(
        package='rviz2',
        executable='rviz2',
        output='screen',
        parameters=[{'use_sim_time': True}],
    )

    # 7. Teleop keyboard（重映射到控制器的 Twist 输入话题）
    teleop_node = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        name='teleop_twist_keyboard',
        prefix='xterm -e',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'speed': 0.1,   # 线速度增量 (m/s)，默认 0.5
            'turn': 0.2,    # 角速度增量 (rad/s)，默认 1.0
        }],
        remappings=[
            ('/cmd_vel', '/ackermann_controller/reference_unstamped')
        ],
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
        slam_toolbox_node,
        rviz2_node,
        teleop_node,
    ])