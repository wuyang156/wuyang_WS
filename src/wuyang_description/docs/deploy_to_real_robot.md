# 导航功能移植到真车教程

本文档详细说明如何将仿真环境中的导航功能移植到实体小车上。

## 目录

- [前提条件](#前提条件)
- [硬件要求](#硬件要求)
- [软件配置差异](#软件配置差异)
- [移植步骤](#移植步骤)
- [启动流程](#启动流程)
- [调试与验证](#调试与验证)
- [常见问题](#常见问题)

---

## 前提条件

### 软件环境
- Ubuntu 22.04
- ROS2 Humble
- Nav2 导航框架
- 已完成的地图文件（通过 SLAM 建图）

### 硬件要求
- Ackermann 转向底盘
- 激光雷达（LiDAR）
- 里程计传感器（编码器或 IMU）
- 车载计算平台（如 Jetson Orin）

---

## 软件配置差异

### 仿真环境 vs 真实环境

| 配置项 | 仿真环境 | 真实环境 |
|--------|---------|---------|
| `use_sim_time` | `true` | `false` |
| Gazebo | 启动 | 不启动 |
| robot_state_publisher | 从 xacro 读取 | 从实际硬件读取 |
| 控制器 | gazebo_ros_control | 真实硬件驱动 |
| TF 发布 | 仿真自动发布 | 需要硬件驱动发布 |

---

## 移植步骤

### 1. 创建真车启动文件

创建 `launch/real_robot_nav.launch.py`，这是真车版本的导航启动文件：

```python
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    pkg_share = get_package_share_directory('wuyang_description')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    # 真车环境使用 sim_time=false
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    
    map_yaml_path = LaunchConfiguration(
        'map',
        default=os.path.join(pkg_share, 'maps', 'real_robot_map', 'map.yaml')
    )
    
    nav2_param_path = LaunchConfiguration(
        'params_file',
        default=os.path.join(pkg_share, 'config', 'nav2_params_real.yaml')
    )

    # === 真实硬件驱动（替换 Gazebo）===
    # 这里需要启动你的底盘驱动节点
    # 示例：
    # robot_driver_node = Node(
    #     package='your_robot_driver',
    #     executable='driver_node',
    #     name='robot_driver',
    #     parameters=[{'use_sim_time': False}],
    # )

    # === TF 发布 ===
    # 如果硬件驱动没有发布 odom -> base_link，需要这个节点
    # odom_publisher_node = Node(
    #     package='your_odom_package',
    #     executable='odom_publisher',
    #     name='odom_publisher',
    #     parameters=[{'use_sim_time': False}],
    # )

    # === 导航系统 ===
    
    # 使用 bringup_launch (包含 AMCL 定位)
    launch_navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [nav2_bringup_dir, '/launch', '/bringup_launch.py']
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'map': map_yaml_path,
            'params_file': nav2_param_path,
        }.items(),
    )

    # === RViz ===
    rviz2_node = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', os.path.join(pkg_share, 'rviz2', 'nav2_default_view.rviz')],
        parameters=[{'use_sim_time': False}],
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument('map', default_value=map_yaml_path),
        DeclareLaunchArgument('params_file', default_value=nav2_param_path),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        # robot_driver_node,  # 取消注释并配置你的驱动
        # odom_publisher_node,  # 如果需要
        launch_navigation,
        rviz2_node,
    ])
```

### 2. 创建真车导航参数文件

复制并修改导航参数：

```bash
cp src/wuyang_description/config/nav2_params.yaml \
   src/wuyang_description/config/nav2_params_real.yaml
```

在 `nav2_params_real.yaml` 中修改以下关键参数：

```yaml
# 所有节点的 use_sim_time 改为 false
use_sim_time: False

# AMCL（启用定位）
amcl:
  ros__parameters:
    use_sim_time: False
    # ... 其他 AMCL 参数根据实际环境调整
    robot_model_type: "nav2_amcl::DifferentialMotionModel"  # 或 OmniMotionModel
    
# 控制器参数可能需要根据真实硬件调整
controller_server:
  ros__parameters:
    use_sim_time: False
    controller_frequency: 20.0  # 根据硬件性能调整
    
    FollowPath:
      desired_linear_vel: 0.2  # 真车速度通常比仿真慢
      lookahead_dist: 0.5      # 根据实际测试调整
      # ... 其他参数
```

### 3. 准备地图文件

确保已通过 SLAM 建图生成真实环境地图：

```bash
# 在真车上建图（如果还没有地图）
ros2 launch wuyang_description slam.launch.py

# 保存地图
ros2 run nav2_map_server map_saver_cli -f ~/maps/real_robot_map

# 将地图文件移动到项目目录
mkdir -p src/wuyang_description/maps/real_robot_map
mv ~/maps/real_robot_map.* src/wuyang_description/maps/real_robot_map/
```

### 4. 配置真车航点

根据真实环境地图，修改 `config/waypoints.yaml` 中的坐标：

```yaml
waypoints:
  - position:
      x: 2.0  # 根据实际地图调整
      y: 1.0
      z: 0.0
    orientation:
      yaw: 0.0
  # ... 添加更多真实环境中的航点
```

---

## 启动流程

### 方案 A：完整导航系统

```bash
# 1. 启动底盘驱动（根据你的硬件）
ros2 launch your_robot_driver robot_driver.launch.py

# 2. 启动激光雷达
ros2 launch rplidar_ros rplidar.launch.py  # 示例

# 3. 启动导航系统
ros2 launch wuyang_description real_robot_nav.launch.py

# 4. 设置初始位姿（在 RViz 中）
# 点击 "2D Pose Estimate" 按钮，在地图上标注小车当前位置和朝向

# 5. 启动顺序导航
ros2 launch wuyang_description sequential_nav.launch.py
```

### 方案 B：分步启动（调试用）

```bash
# 终端 1: 底盘驱动
ros2 launch your_robot_driver robot_driver.launch.py

# 终端 2: 激光雷达
ros2 launch rplidar_ros rplidar.launch.py

# 终端 3: Nav2 导航
ros2 launch nav2_bringup bringup_launch.py \
  use_sim_time:=false \
  map:=/path/to/map.yaml \
  params_file:=/path/to/nav2_params_real.yaml

# 终端 4: RViz
ros2 run rviz2 rviz2 -d /path/to/nav2_default_view.rviz

# 终端 5: 顺序导航
ros2 launch wuyang_description sequential_nav.launch.py
```

---

## 调试与验证

### 1. 检查 TF 树

```bash
# 查看 TF 树结构
ros2 run tf2_tools view_frames

# 应该看到完整的 TF 链：
# map -> odom -> base_link -> laser_frame
```

### 2. 检查话题

```bash
# 查看所有话题
ros2 topic list

# 确认关键话题存在：
# /scan              (激光数据)
# /odom              (里程计)
# /cmd_vel           (速度命令)
# /map               (地图)
# /amcl_pose         (定位结果)
```

### 3. 验证定位

在 RViz 中观察：
- 激光点云应与地图重合
- AMCL 粒子云应收敛到小车周围
- 小车位置估计应准确

### 4. 测试单点导航

```bash
# 手动发送导航目标测试
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: 'map'}, pose: {position: {x: 1.0, y: 0.0, z: 0.0}, orientation: {w: 1.0}}}}"
```

---

## 常见问题

### 1. 小车不动

**可能原因：**
- 底盘驱动未正确订阅 `/cmd_vel`
- 速度命令格式不匹配
- 安全限制（急停按钮、软件限制）

**解决方法：**
```bash
# 检查 cmd_vel 话题
ros2 topic echo /cmd_vel

# 手动发送测试命令
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.1}}" --once
```

### 2. 定位不准确

**可能原因：**
- AMCL 参数未调优
- 激光雷达数据质量差
- 地图与实际环境不符

**解决方法：**
- 调整 AMCL 粒子数量 (`min_particles`, `max_particles`)
- 增大定位更新频率
- 重新建图

### 3. 路径规划失败

**可能原因：**
- 目标点在障碍物内或地图外
- 代价地图配置不合理
- 最小转弯半径设置过大

**解决方法：**
- 在 RViz 中检查代价地图
- 调整 `inflation_radius` 和 `cost_scaling_factor`
- 验证 `minimum_turning_radius` 与真车匹配

### 4. 导航抖动或不稳定

**可能原因：**
- 控制器频率过高或过低
- PID 参数不匹配
- 里程计漂移严重

**解决方法：**
- 调整 `controller_frequency`
- 调整 `lookahead_dist` 和速度参数
- 融合 IMU 数据改善里程计

---

## 性能优化建议

### 1. 降低计算负载

```yaml
# 在 nav2_params_real.yaml 中
global_costmap:
  global_costmap:
    ros__parameters:
      update_frequency: 1.0  # 降低更新频率
      
planner_server:
  ros__parameters:
    expected_planner_frequency: 5.0  # 降低规划频率
```

### 2. 调整速度

根据真车性能调整速度限制：

```yaml
controller_server:
  ros__parameters:
    FollowPath:
      desired_linear_vel: 0.2  # 根据测试调整
      max_angular_accel: 2.0   # 避免过激转向
```

### 3. 安全距离

增加安全边距：

```yaml
global_costmap:
  global_costmap:
    ros__parameters:
      inflation_layer:
        inflation_radius: 0.3  # 增大安全距离
```

---

## 下一步

完成移植后，可以：

1. **记录测试数据**
   ```bash
   ros2 bag record -a -o real_robot_test
   ```

2. **调优参数**
   - 根据实际表现迭代调整 Nav2 参数
   - 记录不同参数组合的效果

3. **添加安全功能**
   - 急停按钮处理
   - 电池电量监控
   - 碰撞检测

4. **扩展功能**
   - 动态避障
   - 多点巡航
   - 任务调度系统

---

## 参考资源

- [Nav2 官方文档](https://navigation.ros.org/)
- [Nav2 参数调优指南](https://navigation.ros.org/tuning/index.html)
- [AMCL 配置指南](https://navigation.ros.org/configuration/packages/configuring-amcl.html)
- [ROS2 Humble 文档](https://docs.ros.org/en/humble/)

---

## 支持

如遇到问题，请检查：
1. 硬件连接是否正常
2. TF 树是否完整
3. 话题数据是否正常发布
4. ROS2 日志输出（`~/.ros/log/`）

祝你移植成功！🚗
