import os
import yaml
from ament_index_python.packages import get_package_share_directory
from launch_ros.actions import Node
from launch import LaunchDescription


def generate_launch_description():
    wheeltec_nav_dir = get_package_share_directory('wheeltec_wuyang_nav2')

    # 从包内 config/waypoints.yaml 读取航点
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
        sequential_navigator_node,
    ])
