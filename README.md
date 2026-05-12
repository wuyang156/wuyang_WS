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
  ros-humble-gazebo-ros-pkgs
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

## Docker 开发环境

项目已配置 `.devcontainer/devcontainer.json`，基于 `ros:humble` 镜像，可直接在 VS Code 中使用 Dev Containers 打开。
