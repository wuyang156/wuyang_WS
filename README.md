# wuyang_description

基于 ROS 2 Humble 的 Ackermann 转向轮式机器人仿真项目，使用 Gazebo 作为物理仿真引擎。

## 环境要求

- **操作系统**：Ubuntu 22.04
- **ROS 2 发行版**：Humble
- **构建工具**：CMake >= 3.8, colcon
- **可选**：Docker（项目已配置 devcontainer）

## 依赖安装

```bash
# 基础工具
sudo apt-get update
sudo apt-get install -y ros-humble-xacro ros-humble-ament-cmake

# 可视化与仿真
sudo apt-get install -y \
  ros-humble-robot-state-publisher \
  ros-humble-joint-state-publisher-gui \
  ros-humble-rviz2 \
  ros-humble-gazebo-ros

# 控制框架
sudo apt-get install -y \
  ros-humble-ros2-control \
  ros-humble-gazebo-ros2-control \
  ros-humble-controller-manager \
  ros-humble-joint-state-broadcaster \
  ros-humble-gazebo-plugins\
  ros-humble-gazebo-ros-pkgs\
  ros-humble-ros2-controllers
```

## 构建

```bash
cd wuyang_ws
colcon build
source install/setup.bash
```

## 使用

```bash
# 可视化模式（仅显示模型，无物理仿真）
ros2 launch wuyang_description display.launch.py

# Gazebo 仿真模式（完整物理仿真）
ros2 launch wuyang_description gazebo.launch.py
```

## 项目结构

```
wuyang_ws/
├── src/wuyang_description/
│   ├── CMakeLists.txt              # CMake 构建配置
│   ├── package.xml                 # ROS 2 包清单
│   ├── config/
│   │   └── ackermann_controller.yaml  # 控制器参数配置
│   ├── launch/
│   │   ├── display.launch.py       # 纯显示启动文件
│   │   └── gazebo.launch.py        # Gazebo 仿真启动文件
│   ├── urdf/
│   │   ├── wuyang_ackermann.urdf.xacro  # 主 URDF 模型
│   │   ├── sensor_laser.urdf.xacro      # 激光雷达传感器
│   │   ├── sensor_camera.urdf.xacro     # 深度相机传感器
│   │   └── gazebo_control.urdf.xacro    # Gazebo 控制接口
│   └── world/
│       └── wuyang_world            # Gazebo 世界文件
├── build/                          # 构建输出
├── install/                        # 安装输出
└── log/                            # 运行日志
```

## 机器人规格

| 参数 | 数值 |
|------|------|
| 轴距 | 0.144 m |
| 前轮距 | 0.158 m |
| 后轮距 | 0.158 m |
| 车轮半径 | 0.034 m |
| 最大线速度 | 1.0 m/s |
| 最大角速度 | 1.5 rad/s |
| 转向角范围 | ±0.6055 rad |

## 传感器

- **激光雷达**：360° 扫描，10m 量程，5Hz 更新率
- **深度相机**：800×600 分辨率，0.15-10m 深度范围，30Hz 更新率

## 话题层级

### 键盘 → 控制器（控制指令输入）

| 发布者 (Publisher) | 话题 (Topic) | 消息类型 | 订阅者 (Subscriber) | 作用 |
|---|---|---|---|---|
| `teleop_twist_keyboard` | `/cmd_vel` | `geometry_msgs/Twist` | —(launch 中重映射)— | 将键盘按键转为运动指令：`linear.x` 控制线速度，`angular.z` 控制转向角 |
| —(重映射后)— | `/ackermann_controller/reference_unstamped` | `geometry_msgs/Twist` | `ackermann_controller` | 控制器接收目标线速度和角速度，驱动后轮滚动和前轮转向 |

### 控制器 → 系统（状态反馈输出）

| 发布者 (Publisher) | 话题 (Topic) | 消息类型 | 订阅者 (Subscriber) | 作用 |
|---|---|---|---|---|
| `ackermann_controller` | `/ackermann_controller/odometry` | `nav_msgs/Odometry` | SLAM、Rviz 等 | 里程计数据：包含机器人实时位姿 (pose) 和速度 (twist)，用于定位和建图 |
| `ackermann_controller` | `/ackermann_controller/tf_odometry` | `tf2_msgs/TFMessage` | `robot_state_publisher`、`rviz2` | 发布 odom → base_link 的坐标变换，维持 TF 树 |
| `ackermann_controller` | `/ackermann_controller/controller_state` | `control_msgs/msg/JointTrajectoryControllerState` | 调试工具 | 控制器内部状态，包括各关节的目标值与实际值 |
| `ackermann_controller` | `/ackermann_controller/transition_event` | `lifecycle_msgs/msg/TransitionEvent` | 调试工具 | 生命周期状态切换日志 |

### Gazebo → 控制器（关节状态输入）

| 发布者 (Publisher) | 话题 (Topic) | 消息类型 | 订阅者 (Subscriber) | 作用 |
|---|---|---|---|---|
| `joint_state_broadcaster` | `/joint_states` | `sensor_msgs/JointState` | `robot_state_publisher`、`ackermann_controller` | 所有关节的实时位置和速度反馈，使 URDF 模型在 Rviz 中同步运动 |

### 数据流简图

```
teleop_twist_keyboard             joint_state_broadcaster (Gazebo)
  │  /cmd_vel                        │  /joint_states
  │  Twist (linear.x, angular.z)     │  JointState (position, velocity)
  ▼                                  ▼
ackermann_steering_controller ──────────────────────────────────────►
  │  odometry (nav_msgs/Odometry)    → SLAM / Rviz
  │  tf_odometry (TFMessage)         → TF 树
  │  controller_state               → 调试
  └──transition_event               → 调试
```

> **重映射说明：** `teleop_twist_keyboard` 默认发布到 `/cmd_vel`，launch 文件中通过 remappings 将 `/cmd_vel` 映射到 `/ackermann_controller/reference_unstamped`，使键盘指令直达控制器。该控制器本版本使用 `reference_unstamped`（类型 `Twist`）而非 `reference`（类型 `AckermannDrive`）。

### 键盘控制

```bash
# 单次测试：前进 0.5 m/s
ros2 topic pub --once /ackermann_controller/reference_unstamped geometry_msgs/msg/Twist "{linear: {x: 0.5}, angular: {z: 0.0}}"

# 持续控制（Ctrl+C 停止）
ros2 topic pub --rate 10 /ackermann_controller/reference_unstamped geometry_msgs/msg/Twist "{linear: {x: 0.5}, angular: {z: 0.0}}"
```

| 按键 | 动作 | 输入 |
|------|------|------|
| `i` | 前进 | linear.x = +0.5 |
| `,` | 后退 | linear.x = −0.5 |
| `j` | 左转 | angular.z = +1.0 |
| `l` | 右转 | angular.z = −1.0 |
| `u` | 左前 | linear.x = +0.5, angular.z = +1.0 |
| `o` | 右前 | linear.x = +0.5, angular.z = −1.0 |
| `k` / `Space` | 停止 | 全零 |


