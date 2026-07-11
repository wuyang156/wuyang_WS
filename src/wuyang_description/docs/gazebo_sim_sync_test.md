# Gazebo 仿真同步功能测试指南

本文档说明 `gazebo.launch.py` 的仿真同步功能及测试方法。

## 功能概述

`gazebo.launch.py` 提供了一个**现实到仿真（Real-to-Sim）同步**测试环境，用于验证真实硬件与仿真环境的一致性。

---

## 架构说明

### 核心组件

```
真实控制命令 → cmd_vel_bridge → Ackermann 控制器 → Gazebo 仿真
                      ↓
                cmd_vel_monitor (延迟监控)
```

### 关键节点

1. **robot_state_publisher**
   - 发布机器人 URDF 模型
   - 维护机器人关节状态

2. **Gazebo**
   - 物理仿真引擎
   - 加载自定义世界文件 (`world/my_world`)

3. **spawn_entity**
   - 在 Gazebo 中生成机器人实体
   - 初始高度 z=0.05m

4. **joint_state_broadcaster**
   - 广播关节状态到 `/joint_states` 话题

5. **ackermann_controller**
   - Ackermann 转向控制器
   - 接收 `/ackermann_controller/reference_unstamped`
   - 发布里程计 TF (`odom -> base_footprint`)

6. **tf_relay_node**
   - 将 `/ackermann_controller/tf_odometry` 中继到 `/tf`
   - 确保 TF 树完整性

7. **teleop_twist_keyboard**
   - 键盘遥控节点
   - 发布 `/cmd_vel` (Twist 消息)

8. **cmd_vel_bridge**
   - **核心同步节点**
   - 将 `/cmd_vel` (Twist) 转换为 Ackermann 控制命令
   - 发布到 `/ackermann_controller/reference_unstamped`

9. **cmd_vel_monitor**
   - Qt GUI 延迟监控工具
   - 实时显示命令延迟和频率

10. **RViz2**
    - 可视化工具
    - 使用 `real2sim.rviz` 配置

---

## 仿真同步机制

### 1. 命令转换流程

```
键盘输入
    ↓
/cmd_vel (geometry_msgs/Twist)
    linear.x: 线速度 (m/s)
    angular.z: 角速度 (rad/s)
    ↓
cmd_vel_bridge (转换节点)
    ↓
/ackermann_controller/reference_unstamped
    (ackermann_msgs/AckermannDriveStamped)
    ↓
Ackermann 控制器
    ↓
Gazebo 物理仿真
```

### 2. 转换算法

`cmd_vel_bridge` 实现 Twist → Ackermann 转换：

```cpp
// 伪代码
linear_velocity = twist.linear.x
angular_velocity = twist.angular.z

// 计算转向角（假设轴距为 wheelbase）
if (linear_velocity != 0) {
    steering_angle = atan(angular_velocity * wheelbase / linear_velocity)
} else {
    steering_angle = 0
}

// 发布 Ackermann 命令
ackermann.speed = linear_velocity
ackermann.steering_angle = steering_angle
```

### 3. TF 树结构

```
map (可选)
  ↓
odom
  ↓
base_footprint
  ↓
base_link
  ├→ wheel_links...
  └→ laser_frame
```

---

## 测试流程

### 1. 启动仿真环境

```bash
cd ~/wuyang_ws
source install/setup.bash
ros2 launch wuyang_description gazebo.launch.py
```

**预期结果：**
- Gazebo 窗口打开，显示小车和环境
- RViz 窗口打开，显示机器人模型
- xterm 终端打开，显示键盘控制说明
- Qt 延迟监控窗口打开

### 2. 键盘控制测试

在 xterm 终端中：

| 按键 | 功能 |
|------|------|
| `i` | 前进 |
| `k` | 停止 |
| `,` | 后退 |
| `j` | 左转 |
| `l` | 右转 |
| `u` | 左前 |
| `o` | 右前 |
| `m` | 左后 |
| `.` | 右后 |
| `q` | 增加速度 |
| `z` | 减少速度 |

**测试步骤：**
1. 按 `i` 让小车前进
2. 观察 Gazebo 中小车运动
3. 观察 RViz 中 TF 和里程计更新
4. 观察延迟监控窗口的数值

### 3. 话题检查

```bash
# 查看所有话题
ros2 topic list

# 关键话题：
# /cmd_vel                                    (键盘输入)
# /ackermann_controller/reference_unstamped   (Ackermann 命令)
# /ackermann_controller/odometry              (里程计)
# /joint_states                               (关节状态)
# /tf                                         (TF 变换)
```

### 4. 延迟监控

cmd_vel_monitor 显示的信息：
- **命令接收频率**：应为 10-20 Hz (取决于键盘输入)
- **转换延迟**：应 < 5ms
- **发布延迟**：应 < 10ms

**健康指标：**
- ✅ 延迟 < 20ms
- ⚠️ 延迟 20-50ms（可接受）
- ❌ 延迟 > 50ms（需要优化）

### 5. TF 验证

```bash
# 查看 TF 树
ros2 run tf2_tools view_frames

# 查看特定 TF
ros2 run tf2_ros tf2_echo odom base_footprint
```

**预期输出：**
- 应看到实时更新的位置和方向
- 当小车移动时，数值应连续变化

### 6. 里程计验证

```bash
# 订阅里程计话题
ros2 topic echo /ackermann_controller/odometry

# 观察：
# - pose: 位置应随移动更新
# - twist: 速度应与 cmd_vel 对应
```

---

## 同步精度测试

### 测试 1: 直线运动

```bash
# 发布恒定速度
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.2}, angular: {z: 0.0}}" -r 10

# 观察 10 秒后停止
# 测量 Gazebo 中小车实际移动距离
# 理论距离 = 0.2 m/s × 10 s = 2.0 m
# 允许误差：± 5%
```

### 测试 2: 转向精度

```bash
# 发布转向命令
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.2}, angular: {z: 0.5}}" -r 10

# 观察转弯半径
# 理论转弯半径 = v / ω = 0.2 / 0.5 = 0.4 m
# 验证仿真中的实际轨迹
```

### 测试 3: 响应延迟

```python
# 使用 Python 脚本测试
import rclpy
from geometry_msgs.msg import Twist
import time

# 记录发送时间戳
send_time = time.time()

# 发布命令
pub.publish(twist_msg)

# 在 Gazebo 中观察小车开始移动的时间
# 计算延迟 = 开始移动时间 - 发送时间
# 目标：< 50ms
```

---

## 真实硬件对比测试

### 准备工作

1. **记录仿真数据**
   ```bash
   ros2 bag record /cmd_vel /ackermann_controller/odometry /tf
   ```

2. **在真车上执行相同命令**
   - 使用相同的 `/cmd_vel` 命令序列
   - 记录真车的运动轨迹

3. **对比分析**
   - 比较里程计轨迹
   - 比较转向响应
   - 识别差异来源

### 对比指标

| 指标 | 仿真环境 | 真实环境 | 允许差异 |
|------|---------|---------|---------|
| 最大线速度 | 0.28 m/s | ? | ±10% |
| 最大角速度 | 1.0 rad/s | ? | ±15% |
| 转弯半径 | 0.22 m | ? | ±10% |
| 加速度 | 2.5 m/s² | ? | ±20% |
| 响应延迟 | <50ms | ? | <100ms |

---

## 参数调优

### 如果仿真与真车不匹配

#### 1. 调整控制器参数

编辑 `urdf/wuyang_ackermann.urdf.xacro` 中的控制器配置：

```xml
<plugin name="ackermann_controller" filename="libgazebo_ros2_control.so">
  <parameters>$(find wuyang_description)/config/ackermann_controller.yaml</parameters>
</plugin>
```

#### 2. 调整物理参数

在 URDF 中修改：
- 质量和惯性
- 摩擦系数
- 车轮半径
- 轴距

#### 3. 调整 cmd_vel_bridge 参数

如果转换算法需要调整，修改 `src/cmd_vel_bridge.cpp`：

```cpp
// 调整轴距
const double wheelbase = 0.144;  // 根据真车测量

// 调整限幅
const double max_steering_angle = 0.6055;  // 最大转向角
const double max_speed = 0.28;             // 最大速度
```

---

## 故障排查

### 问题 1: 小车不动

**检查：**
```bash
# 1. 检查控制器是否加载
ros2 control list_controllers

# 应该看到：
# ackermann_controller[ackermann_steering_controller/AckermannSteeringController] active
# joint_state_broadcaster[joint_state_broadcaster/JointStateBroadcaster] active

# 2. 检查 cmd_vel_bridge 是否运行
ros2 node list | grep cmd_vel_bridge

# 3. 监听 Ackermann 命令
ros2 topic echo /ackermann_controller/reference_unstamped
```

### 问题 2: 延迟过大

**可能原因：**
- CPU 负载过高
- Gazebo 实时因子 < 1.0
- 网络延迟（如果使用远程显示）

**解决方法：**
- 关闭不必要的插件
- 降低 Gazebo 更新频率
- 使用本地显示

### 问题 3: TF 树断裂

**检查：**
```bash
# 查看 TF 树
ros2 run tf2_tools view_frames

# 检查 tf_relay 是否工作
ros2 topic hz /tf
```

---

## 高级测试

### 1. 路径跟踪精度

```python
# 发布预定义路径
# 记录实际轨迹
# 计算路径跟踪误差
```

### 2. 多次往返测试

```python
# 让小车前进后退多次
# 验证里程计累积误差
# 对比仿真与真车的漂移量
```

### 3. 极限工况测试

- 最大速度转向
- 急停响应
- 连续 S 形弯道

---

## 数据分析

### 使用 rosbag 分析

```bash
# 回放记录
ros2 bag play test_data.db3

# 使用 plotjuggler 可视化
ros2 run plotjuggler plotjuggler
```

### 分析脚本示例

```python
import rosbag2_py
import matplotlib.pyplot as plt

# 读取 bag 文件
# 提取 cmd_vel 和 odometry
# 绘制速度-时间曲线
# 计算响应延迟
```

---

## 总结

`gazebo.launch.py` 提供的仿真同步功能允许你：

✅ 在安全环境中测试控制算法
✅ 验证 cmd_vel → Ackermann 转换正确性
✅ 测量系统响应延迟
✅ 为真车部署提供参考数据

**下一步：**
1. 完成仿真环境测试
2. 记录关键参数
3. 在真车上复现测试
4. 迭代调优直到仿真与真车行为一致

---

## 相关文档

- [真车部署教程](deploy_to_real_robot.md)
- [导航功能说明](sequential_navigation.md)
- [Ackermann 控制器配置](../config/ackermann_controller.yaml)

祝测试顺利！🚗💨
