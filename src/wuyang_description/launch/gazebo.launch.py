from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, RegisterEventHandler
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.event_handlers import OnProcessExit
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    pkg_share = FindPackageShare('wuyang_description')
    gazebo_ros_share = FindPackageShare('gazebo_ros')
    ackermann_urdf_file = PathJoinSubstitution([pkg_share, 'urdf', 'wuyang_ackermann.urdf.xacro'])

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{
            'robot_description': ParameterValue(Command(['xacro ', ackermann_urdf_file]), value_type=str),
            'use_sim_time': True
        }]
    )
 
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([gazebo_ros_share, 'launch', 'gazebo.launch.py'])
        ),
        launch_arguments={
            'world': PathJoinSubstitution([pkg_share, 'world', 'my_world'])
        }.items()
    )
 
    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-topic', '/robot_description', '-entity', 'wuyang_car', '-z', '0.05'],
        output='screen'
    )

    load_joint_state_broadcaster = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster"],
    )

    load_ackermann_controller = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["ackermann_controller"],
    )

    # TF 中继（odom → base_footprint 注入 /tf）
    tf_relay_node = Node(
        package='topic_tools',
        executable='relay',
        name='tf_relay',
        arguments=['/ackermann_controller/tf_odometry', '/tf'],
    )

    rviz2_node = Node(
        package='rviz2',
        executable='rviz2',
        output='screen',
    )

    # 键盘控制
    teleop_node = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        name='teleop_twist_keyboard',
        prefix='xterm -e',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'speed': 0.1,   # 线速度增量 (m/s)
            'turn': 0.2,    # 角速度增量 (rad/s)
        }],
        remappings=[
            ('/cmd_vel', '/ackermann_controller/reference_unstamped')
        ],
    )

    return LaunchDescription([
        robot_state_publisher_node,
        gazebo,
        spawn_entity,
        rviz2_node,
        tf_relay_node,
        teleop_node,
        
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=spawn_entity,
                on_exit=[load_joint_state_broadcaster],
            )
        ),
        
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=load_joint_state_broadcaster,
                on_exit=[load_ackermann_controller],
            )
        ),
    ])