import os
import launch_ros.actions
from launch import LaunchDescription
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    wheeltec_nav_dir = get_package_share_directory('wheeltec_wuyang_nav2')

    # 主保存路径：包内 map 目录（需要重新编译才能持久化）
    map_install_path = os.path.join(wheeltec_nav_dir, 'map', 'WHEELTEC')
    # 备份路径：home 目录，方便直接使用
    map_home_path = os.path.expanduser('~/WHEELTEC_map')

    map_saver = launch_ros.actions.Node(
        package='nav2_map_server',
        executable='map_saver_cli',
        name='map_saver',
        output='screen',
        arguments=['-f', map_install_path],
        parameters=[{
            'save_map_timeout': 20000.0,
            'free_thresh_default': 0.196,
        }],
    )

    map_backup = launch_ros.actions.Node(
        package='nav2_map_server',
        executable='map_saver_cli',
        name='map_saver_backup',
        output='screen',
        arguments=['-f', map_home_path],
        parameters=[{
            'save_map_timeout': 20000.0,
            'free_thresh_default': 0.196,
        }],
    )

    ld = LaunchDescription()
    ld.add_action(map_saver)
    ld.add_action(map_backup)
    return ld
 
