import os
import yaml
from ament_index_python.packages import get_package_share_directory
from launch_ros.actions import Node
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')

    wheeltec_robot_dir  = get_package_share_directory('turn_on_wheeltec_robot')
    wheeltec_launch_dir = os.path.join(wheeltec_robot_dir, 'launch')

    wheeltec_nav_dir       = get_package_share_directory('wheeltec_wuyang_nav2')
    wheeltec_nav_launch_dir = os.path.join(wheeltec_nav_dir, 'launch')

    map_file = LaunchConfiguration(
        'map',
        default=os.path.join(wheeltec_nav_dir, 'map', 'WHEELTEC.yaml'))

    param_file = LaunchConfiguration(
        'params_file',
        default=os.path.join(wheeltec_nav_dir, 'param', 'wheeltec_params', 'param_odom_akm.yaml'))

    initial_pose_x   = LaunchConfiguration('initial_pose_x',   default='0.0')
    initial_pose_y   = LaunchConfiguration('initial_pose_y',   default='0.0')
    initial_pose_yaw = LaunchConfiguration('initial_pose_yaw', default='0.0')

    # 从包内 config/waypoints.yaml 读取航点，传给 sequential_navigator
    waypoints_yaml = os.path.join(wheeltec_nav_dir, 'config', 'waypoints.yaml')
    with open(waypoints_yaml, 'r') as f:
        wp_config = yaml.safe_load(f)
    waypoint_list = []
    for wp in wp_config['waypoints']:
        waypoint_list.extend([
            wp['position']['x'],
            wp['position']['y'],
            wp['position']['z'],
            wp['orientation']['yaw'],
        ])

    sequential_navigator_node = Node(
        package='wheeltec_wuyang_nav2',
        executable='sequential_navigator',
        name='sequential_navigator',
        output='screen',
        parameters=[{
            'use_sim_time': False,
            'waypoints': waypoint_list,
        }],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'map',
            default_value=map_file,
            description='Full path to map yaml file to load'),

        DeclareLaunchArgument(
            'params_file',
            default_value=param_file,
            description='Full path to nav2 params file to load'),

        DeclareLaunchArgument(
            'initial_pose_x',
            default_value=initial_pose_x,
            description='Initial X of robot in map frame (m)'),

        DeclareLaunchArgument(
            'initial_pose_y',
            default_value=initial_pose_y,
            description='Initial Y of robot in map frame (m)'),

        DeclareLaunchArgument(
            'initial_pose_yaw',
            default_value=initial_pose_yaw,
            description='Initial yaw of robot in map frame (rad)'),

        # 底盘驱动 + 传感器（雷达、相机、IMU、EKF）
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(wheeltec_launch_dir, 'wheeltec_sensors.launch.py')),
        ),

        # Nav2 导航栈（纯里程计定位，无 AMCL）
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(wheeltec_nav_launch_dir, 'bringup_odom_launch.py')),
            launch_arguments={
                'map':              map_file,
                'use_sim_time':     use_sim_time,
                'params_file':      param_file,
                'initial_pose_x':   initial_pose_x,
                'initial_pose_y':   initial_pose_y,
                'initial_pose_yaw': initial_pose_yaw,
            }.items(),
        ),

        # 顺序导航节点
        sequential_navigator_node,
    ])
