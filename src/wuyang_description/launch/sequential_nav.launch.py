import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    pkg_share = get_package_share_directory('wuyang_description')
    waypoints_yaml = os.path.join(pkg_share, 'config', 'waypoints.yaml')

    # 从YAML文件手动解析航点
    # 由于ROS2参数系统的限制，我们需要将YAML转换为参数列表
    import yaml
    with open(waypoints_yaml, 'r') as f:
        config = yaml.safe_load(f)

    # 将航点转换为扁平列表: [x, y, z, yaw, x, y, z, yaw, ...]
    waypoint_list = []
    for wp in config['waypoints']:
        waypoint_list.extend([
            wp['position']['x'],
            wp['position']['y'],
            wp['position']['z'],
            wp['orientation']['yaw']
        ])

    sequential_navigator_node = Node(
        package='wuyang_description',
        executable='sequential_navigator',
        name='sequential_navigator',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'waypoints': waypoint_list,
        }],
    )

    return LaunchDescription([
        sequential_navigator_node,
    ])
