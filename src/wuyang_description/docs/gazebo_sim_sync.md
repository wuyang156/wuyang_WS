# Gazebo 仿真同步包

## 概述

`wuyang_description` 是一个 **Gazebo 仿真同步包**，用于在 Gazebo 中运行小车仿真模型，接受与真车相同的 `/cmd_vel` 控制话题，实现对真车的仿真模仿。

---

## Launch 文件说明

### 比赛用 Launch 文件

| 文件 | 用途 |
|------|------|
| `launch/gazebo.launch.py` | **正式比赛使用的 launch 文件**，启动完整的 Gazebo 仿真环境 |

该 launch 文件启动以下组件：

1. **robot_state_publisher** — 加载 URDF/Xacro 模型
2. **Gazebo** — 启动仿真环境（使用 `world/my_world`）
3. **spawn_entity** — 在 Gazebo 中生成小车实体
4. **controller_manager** — 加载 `joint_state_broadcaster` 和 `ackermann_controller`
5. **tf_relay** — 将 `/ackermann_controller/tf_odometry` 中继到 `/tf`
6. **cmd_vel_bridge** — `/cmd_vel` 桥接节点（见下方说明）
7. **cmd_vel_monitor** — Qt 延迟监控弹窗（见下方说明）

### 其他 Launch 文件

其余 `launch/` 目录下的文件为 **开发过程中产生的中间测试文件**，非正式比赛使用：

| 文件 | 性质 |
|------|------|
| `launch/display.launch.py` | 中间开发测试 |
| `launch/slam.launch.py` | 中间开发测试 |
| `launch/vslam.launch.py` | 中间开发测试 |
| `launch/nav.launch.py` | 中间开发测试 |
| `launch/sequential_nav.launch.py` | 中间开发测试 |

---

## 与真车的关系

### 话题冲突（不影响仿真）

部分传感器话题以及 `base` / `base_footprint` 坐标系与真车存在冲突，但这**不影响 Gazebo 中的车辆接受控制话题并做出模仿**。原因在于仿真端的控制逻辑与真车不同（见下方）。

### 控制逻辑差异

真车和仿真端的控制逻辑不同：

- **真车**：直接通过底层硬件接受控制指令
- **仿真端**：需要通过 `cmd_vel_bridge.cpp` 将通用的 `/cmd_vel`（`geometry_msgs/Twist`）转换为 Gazebo 中 Ackermann 控制器可接受的控制话题

---

## cmd_vel_bridge 桥接节点

**源文件**：`src/cmd_vel_bridge.cpp`

该节点负责将 `/cmd_vel` 话题桥接到 `/ackermann_controller/reference_unstamped`：

```
/cmd_vel  ──→  cmd_vel_bridge  ──→  /ackermann_controller/reference_unstamped
```

**转换逻辑**：
- `linear.x`：直接透传
- `angular.z`：将角速度转换为前轮转向角，公式为 `atan2(L × ω, v)`，其中 `L = 0.144m`（轴距）

---

## cmd_vel_monitor 延迟监控

**源文件**：`src/cmd_vel_monitor.cpp`

内置 **Qt 弹窗** 用于实时监控 `/cmd_vel` 话题的网络延迟。

### 延迟计算原理

通过 DDS 层的时间戳计算延迟：

```
延迟 = received_timestamp − source_timestamp
```

- `source_timestamp`：发布端 `publish()` 时自动打戳
- `received_timestamp`：接收端收到消息时打戳

### 延迟评级

| 延迟范围 | 评级 |
|----------|------|
| < 20 ms | ● 优秀 — 实时控制 |
| 20–50 ms | ● 良好 — 轻微延迟 |
| 50–100 ms | ● 可接受 — 明显延迟 |
| 100–300 ms | ● 较差 — 控制受影响 |
| > 300 ms | ● 严重 — 基本不可用 |

每 2 秒采样一次最新消息的时延并刷新显示。

### 时间同步要求

**延迟测算需要小车端和仿真端运行命令同步时间戳才可以生效**，否则测量值将包含时钟偏差。

弹窗底部显示了如何进行 NTP 时钟同步的提示，具体同步命令在弹窗界面中有显示。跨机器测量需两端 NTP 时钟同步，否则值含时钟偏差。
