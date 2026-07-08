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

```
键盘遥控                    控制器                          ROS 2 生态
teleop_twist_keyboard ────► ackermann_steering_controller
                                 │
/cmd_vel                        │  参考输入
  geometry_msgs/Twist  ─────────┤  /ackermann_controller/reference_unstamped
                                │    geometry_msgs/Twist
  linear.x ────────── 线速度 ────┤
  angular.z ───────── 转向角 ────┤
                                │
                                │  状态输出
                                │  /ackermann_controller/odometry
                                │    nav_msgs/Odometry
                                │
                                ├──/ackermann_controller/controller_state
                                ├──/ackermann_controller/tf_odometry
                                └──/ackermann_controller/transition_event

/joint_states ←── joint_state_broadcaster ←── Gazebo 关节状态
  sensor_msgs/JointState
```

> **关键点：** 该版本控制器通过 `reference_unstamped`（类型 `geometry_msgs/Twist`）接收运动指令，而非 `reference`（类型 `ackermann_msgs/AckermannDrive`）。`teleop_twist_keyboard` 的重映射目标须为 `reference_unstamped`。

### 键盘控制命令

```bash
# 手动发布：前进 0.5 m/s
ros2 topic pub --once /ackermann_controller/reference_unstamped geometry_msgs/msg/Twist "{linear: {x: 0.5}, angular: {z: 0.0}}"

# 持续发布（Ctrl+C 停止）
ros2 topic pub --rate 10 /ackermann_controller/reference_unstamped geometry_msgs/msg/Twist "{linear: {x: 0.5}, angular: {z: 0.0}}"
```

| 按键 | 动作 |
|------|------|
| `i` | 前进 |
| `,` | 后退 |
| `j` | 左转 |
| `l` | 右转 |
| `u` | 左前 |
| `o` | 右前 |
| `k` / `Space` | 停止 |


