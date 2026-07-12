# wheeltec_wuyang_nav2 — 真车纯里程计导航功能包

## 概述

本包需要复制到**轮趣小车的工作空间**，通过 `colcon build` 编译后使用，是用于**真车纯里程计导航**的功能包。

> **纯里程计导航**：本方案不依赖 AMCL（自适应蒙特卡洛定位），而是直接使用里程计（odometry）作为定位源，因此需要在启动前将小车放置在已知的出发点。

---

## 目录结构

```
wheeltec_wuyang_nav2/
├── launch/
│   ├── wheeltec_nav2.launch.py       # 纯里程计导航启动文件
│   ├── sequential_nav.launch.py      # 序列化导航点启动文件
│   └── bringup_odom_launch.py        # Nav2 导航栈启动（内部调用）
├── config/
│   └── waypoints.yaml                # 导航点阵配置文件
├── map/
│   └── WHEELTEC.yaml                 # 地图文件
└── param/
    └── wheeltec_params/
        └── param_odom_akm.yaml       # 里程计导航参数
```

---

## 编译与使用

```bash
# 1. 将本包复制到小车工作空间的 src 目录下
# 2. 编译
cd ~/your_ws
colcon build --packages-select wheeltec_wuyang_nav2
source install/setup.bash
```

---

## 远程可视化

当自己的电脑与小车处于**同一局域网**时，在自己电脑上启动 RViz2 和 rqt 几乎与在小车上直接启动等同。因此推荐用自己电脑运行 RViz2 来管理导航，无需在小车上外接显示器。

```bash
# 在自己电脑上（需配置 ROS_DOMAIN_ID 与小车一致）
rviz2
rqt
```

> 确保两台设备的 `ROS_DOMAIN_ID` 环境变量一致，且网络互通，即可直接订阅小车上的话题进行可视化和监控。

---

## 额外功能开发

额外功能分为两个部分，对应两个 launch 文件：

### 1. 序列化导航点 — `sequential_nav.launch.py`

启动**序列化导航点**功能，小车会按照预设的航点按顺序依次导航。

**导航点配置**：修改 `config/waypoints.yaml` 即可增删或修改导航点阵。

```yaml
# config/waypoints.yaml
waypoints:
  - position:    { x: 1.0, y: 0.5, z: 0.0 }
    orientation: { yaw: 0.0 }
  - position:    { x: 2.0, y: 1.0, z: 0.0 }
    orientation: { yaw: 1.57 }
  # 按需增删...
```

```bash
ros2 launch wheeltec_wuyang_nav2 sequential_nav.launch.py
```

### 2. 纯里程计导航 — `wheeltec_nav2.launch.py`

纯里程计导航功能的**完整启动文件**，依次启动以下组件：

| 组件 | 说明 |
|------|------|
| 底盘驱动 + 传感器 | 雷达、相机、IMU、EKF |
| Nav2 导航栈 | 纯里程计定位，无 AMCL |
| `cmd_vel_interceptor` | 视觉-速度拦截节点 |

> **⚠️ 重要**：底盘启动前，**一定要把小车放在出发点、车头朝外**。运行后小车会刷新在 RViz2 全局代价地图可视化图像的出发点对应位置。

**默认初始位姿参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `initial_pose_x` | `0.8` | 初始 X 坐标 (m) |
| `initial_pose_y` | `0.5` | 初始 Y 坐标 (m) |
| `initial_pose_yaw` | `-1.5708` | 初始偏航角 (rad) |

```bash
# 使用默认参数启动
ros2 launch wheeltec_wuyang_nav2 wheeltec_nav2.launch.py

# 指定自定义初始位姿
ros2 launch wheeltec_wuyang_nav2 wheeltec_nav2.launch.py \
    initial_pose_x:=0.0 \
    initial_pose_y:=0.0 \
    initial_pose_yaw:=0.0
```

---

### 视觉-速度拦截节点

`cmd_vel_interceptor` 是本功能包与 **lzj 的视觉感知包**之间的桥梁节点。它在不影响 Nav2 全局路径规划的前提下，根据视觉感知结果对底盘速度指令进行实时干预，使小车在自主导航过程中具备对交通信号、行人、障碍物等视觉事件的即时响应能力。

#### 话题拓扑

```
┌──────────────┐     /origin_cmd       ┌──────────────────────┐     /cmd_vel      ┌──────────┐
│  Nav2 导航栈  │ ──────────────────→  │  cmd_vel_interceptor │ ──────────────→  │  底盘驱动  │
│ (controller)  │                      │                      │                  │          │
└──────────────┘                      │     /visual_result    │                  └──────────┘
                                      │  ←────────────────── │
                                      └──────────────────────┘
                                              ↑
                                      ┌──────────────┐
                                      │  lzj 视觉节点  │
                                      │ (交通灯/行人/  │
                                      │  标志识别等)   │
                                      └──────────────┘
```

| 话题 | 方向 | 类型 | 说明 |
|------|------|------|------|
| `/origin_cmd` | 订阅 | `geometry_msgs/Twist` | Nav2 controller_server 输出的原始速度指令（Nav2 配置中 `cmd_vel_topic` 已改为 `/origin_cmd`） |
| `/visual_result` | 订阅 | `std_msgs/Int32` | lzj 视觉感知节点发布的标志位（0~4） |
| `/cmd_vel` | 发布 | `geometry_msgs/Twist` | 经视觉判定和速度平滑后的最终底盘速度指令 |

#### 工作原理：为什么不影响全局路径规划？

这是整个拦截机制的核心设计：**Nav2 导航栈完全不知道自己的指令被拦截了**。

1. **话题重定向**：Nav2 参数中将 `controller_server` 的 `cmd_vel_topic` 配置为 `/origin_cmd` 而非 `/cmd_vel`，因此 Nav2 输出的速度指令不会直接到达底盘，而是先经过拦截节点。

2. **透明拦截**：Nav2 的全局规划器（planner）、控制器（controller）、行为树（BT）等所有模块照常运行——它们持续接收传感器数据、更新代价地图、计算路径、生成速度指令。拦截节点在 Nav2 的视野之外工作，Nav2 无从感知下游的速度修改。

3. **状态连续性**：
   - 当视觉感知到红灯/行人/停车标志时，拦截节点让底盘**平滑停车**，但 Nav2 控制器仍按原计划输出速度指令。此时 Nav2 会认为"机器人没有按预期移动"，可能触发局部路径重新规划或恢复行为，但这些都是 Nav2 的正常运作——一旦视觉解除、拦截节点恢复速度透传，Nav2 会自行从当前位置继续导航。
   - 当视觉恢复为 `NORMAL` 时，拦截节点通过**斜坡函数**将速度平滑回升至 Nav2 指令值，避免了速度跳变对里程计积分精度的冲击。

4. **SLOW 模式的特殊之处**：与停车类标志不同，SLOW 模式不是将速度降为零，而是按 `slow_ratio`（默认 0.4）等比缩放线速度和角速度。这意味着小车只是减速慢行，导航仍在进行——视觉感知发现需要减速的区域通过后，自动恢复全速。

#### 视觉标志位定义

lzj 视觉包通过 `/visual_result` 话题发布 `Int32` 型标志位，含义如下：

| 标志值 | 枚举 | 行为 | 说明 |
|--------|------|------|------|
| `0` | `NORMAL` | 直接透传 | 路况正常，Nav2 原始指令无修改地发布到 `/cmd_vel` |
| `1` | `RED_LIGHT` | 平滑停车 | 检测到红灯，速度平滑降至零 |
| `2` | `SLOW` | 降速至 40% | 检测到减速标志或需要慢行的区域，线速度和角速度等比缩放 |
| `3` | `PEDESTRIAN` | 平滑停车 | 检测到行人横穿，速度平滑降至零 |
| `4` | `STOP` | 平滑停车 | 检测到停车标志/紧急情况，速度平滑降至零 |

#### 平滑加减速机制

为避免速度突变导致里程计积分误差或底盘抖动，拦截节点使用**斜坡函数（ramp）**约束每次速度更新的最大变化量：

```
每个 tick 最大变化量 = max_decel × (1 / publish_rate)
```

以默认参数为例：`max_decel = 0.5 m/s²`、`publish_rate = 30 Hz`，则每个 tick（~33ms）线速度最多变化 `0.5 × 0.033 ≈ 0.017 m/s`。若当前速度为 0.5 m/s，从开始减速到完全停止约需 1 秒，过程平滑不突兀。

#### 超时安全回退

若 `/visual_result` 话题超过 `visual_timeout`（默认 1 秒）未收到新消息，拦截节点自动将标志位按 `NORMAL` 处理，确保即使视觉节点异常退出，导航功能也不会被永久阻塞。

#### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `publish_rate` | `30.0` Hz | 输出发布频率，与 Nav2 controller_server 保持一致 |
| `max_decel` | `0.5` m/s² | 线速度最大减速度（也是最大加速度） |
| `max_ang_decel` | `1.0` rad/s² | 角速度最大减速度 |
| `slow_ratio` | `0.4` | SLOW 模式速度倍率，0.4 表示降至正常速度的 40% |
| `visual_timeout` | `1.0` s | 视觉话题超时，超时后退回 `NORMAL` 保证导航不中断 |
