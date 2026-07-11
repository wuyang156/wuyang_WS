# Gazebo 实车同步仿真使用说明

本文档说明 `gazebo.launch.py` 的组成、使用前提与操作步骤。

---

## 功能概述

`ros2 launch wuyang_description gazebo.launch.py` 一键启动以下组件：

| 组件 | 说明 |
|------|------|
| Gazebo | 加载仿真世界，生成车辆模型 |
| robot_state_publisher | 发布机器人 TF 树 |
| joint_state_broadcaster | 广播关节状态 |
| ackermann_controller | 阿克曼转向控制器 |
| tf_relay | 将里程计 TF 注入 `/tf` |
| RViz2 | 使用 `real2sim.rviz` 配置启动 |
| teleop_twist_keyboard | xterm 窗口键盘控制，发布到 `/cmd_vel` |
| **cmd_vel_bridge** | 订阅 `/cmd_vel`，将角速度转换为前轮转向角，发布到 `/ackermann_controller/reference_unstamped` |
| **cmd_vel_monitor** | Qt5 弹窗，每 2 秒采样一次，显示最新消息的网络延迟及评级 |

---

## 使用前提

### 1. 环境依赖

```bash
# 安装所有声明的依赖（包括 qtbase5-dev）
cd ~/wuyang_ws
rosdep install --from-paths src --ignore-src -r -y
```

### 2. 编译

```bash
colcon build --packages-select wuyang_description
source install/setup.bash
```

### 3. ROS2 网络配置（跨机器同步时）

实车与仿真机需处于同一 ROS2 网络，即 `ROS_DOMAIN_ID` 相同：

```bash
# 两台机器均执行（值保持一致，例如 42）
export ROS_DOMAIN_ID=42
```

建议写入 `~/.bashrc` 永久生效：

```bash
echo 'export ROS_DOMAIN_ID=42' >> ~/.bashrc
source ~/.bashrc
```

### 4. 时钟同步（延迟监控的必要条件）

`cmd_vel_monitor` 使用 DDS 层的 `source_timestamp`（发布端打戳）与 `received_timestamp`（接收端打戳）之差计算延迟。**若两台机器时钟不同步，测量值将叠加时钟偏差，无参考意义。**

在实车和仿真机上分别执行：

```bash
# 手动同步一次
sudo ntpdate -u pool.ntp.org

# 或启用 systemd-timesyncd 持续同步
sudo systemctl enable --now systemd-timesyncd
timedatectl show          # 确认 NTPSynchronized=yes
```

> 局域网内 NTP 通常可将时钟偏差控制在 **1–10 ms** 以内，满足延迟评估需求。如需更高精度（亚毫秒），可使用 PTP（`linuxptp`）。

---

## 启动方式

```bash
ros2 launch wuyang_description gazebo.launch.py
```

启动后会自动弹出：
- Gazebo 仿真窗口
- RViz2 可视化窗口（加载 `real2sim.rviz`）
- xterm 键盘控制窗口
- Qt5 延迟监控弹窗

---

## 延迟监控说明

`cmd_vel_monitor` 弹窗每 **2 秒**采样一次最新消息的端到端延迟，并给出评级：

| 延迟范围 | 评级 | 说明 |
|----------|------|------|
| < 20 ms | ● 优秀 | 可实时同步控制 |
| 20–50 ms | ● 良好 | 轻微延迟，不影响使用 |
| 50–100 ms | ● 可接受 | 明显延迟，建议优化网络 |
| 100–300 ms | ● 较差 | 控制响应受影响 |
| > 300 ms | ● 严重 | 基本不可用，请检查网络连接 |

> 延迟测量基于 DDS 时间戳，不需要修改消息类型，但**必须满足时钟同步前提**。

---

## cmd_vel_bridge 转换原理

键盘控制（`teleop_twist_keyboard`）发布的 `Twist` 消息中：
- `linear.x`：期望线速度（m/s）
- `angular.z`：期望角速度（rad/s）

`cmd_vel_bridge` 将角速度转换为阿克曼前轮转向角后再发布：

$$\delta = \arctan\!\left(\frac{L \cdot \omega}{v}\right)$$

其中 $L = 0.144\ \mathrm{m}$（轴距），$\omega$ 为角速度，$v$ 为线速度。

转换结果以相同的 `Twist` 格式发布到 `/ackermann_controller/reference_unstamped`：
- `linear.x`：线速度（不变）
- `angular.z`：前轮转向角（弧度）

---

## Nav2 场景

导航时，`cmd_vel_to_ackermann.py` 脚本承担相同的转换职责，订阅 Nav2 输出的 `/cmd_vel_nav`：

```bash
ros2 run wuyang_description cmd_vel_to_ackermann.py \
  --ros-args -p input_topic:=/cmd_vel_nav
```
