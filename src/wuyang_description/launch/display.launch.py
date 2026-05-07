from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_share = get_package_share_directory("wuyang_description")

    ackermann_model_arg = DeclareLaunchArgument(
        "ackermann_model",
        default_value=PathJoinSubstitution([pkg_share, "urdf", "wuyang_ackermann.urdf.xacro"]),
        description="Absolute path to the URDF/xacro model file",
    )

    robot_description_content = ParameterValue(
        Command(
            ["xacro ", LaunchConfiguration("ackermann_model")]
        ),
        value_type=str
    )

    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{"robot_description": robot_description_content}],
    )

    joint_state_publisher_gui_node = Node(
        package="joint_state_publisher_gui",
        executable="joint_state_publisher_gui",
    )

    rviz2_node = Node(
        package="rviz2",
        executable="rviz2",
        output="screen",
    )

    return LaunchDescription([
        ackermann_model_arg,
        robot_state_publisher_node,
        joint_state_publisher_gui_node,
        rviz2_node,
    ])
