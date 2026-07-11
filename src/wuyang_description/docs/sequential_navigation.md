# 顺序导航节点使用说明

## 功能概述

`sequential_navigator` 是一个按顺序导航到多个目标点的ROS2节点，基于Nav2的`navigate_to_pose`动作实现。

## 文件说明

- **节点源码**: `src/sequential_navigator.cpp`
- **配置文件**: `config/waypoints.yaml`
- **启动文件**: `launch/sequential_nav.launch.py`

## 配置航点

编辑 `config/waypoints.yaml` 文件来配置导航点：

```yaml
waypoints:
  - position:
      x: 1.0
      y: 0.0
      z: 0.0
    orientation:
      yaw: 0.0  # 朝向角度（弧度）

  - position:
      x: 1.5
      y: -0.5
      z: 0.0
    orientation:
      yaw: -1.5708  # -90度，朝向y负向
```

### 方向角度参考

- `0.0` = 朝向x正向（东）
- `1.5708` (π/2) = 朝向y正向（北）
- `3.14159` (π) = 朝向x负向（西）
- `-1.5708` (-π/2) = 朝向y负向（南）

## 使用方法

### 1. 启动导航环境

首先启动基础导航系统：

```bash
ros2 launch wuyang_description nav.launch.py
```

### 2. 启动顺序导航节点

在新终端中启动顺序导航：

```bash
ros2 launch wuyang_description sequential_nav.launch.py
```

### 3. 查看导航状态

节点会在终端输出当前导航状态：
- 航点加载信息
- 当前导航的航点序号和坐标
- 每个航点的导航结果（成功/失败）

## 节点特性

1. **按顺序执行**: 严格按照YAML文件中的顺序导航
2. **失败处理**: 如果某个航点导航失败，会记录错误但不影响整体流程
3. **延迟控制**: 到达一个航点后延迟1秒再导航到下一个
4. **灵活配置**: 可以在YAML中配置任意数量的航点

## 节点参数

- `use_sim_time` (bool): 是否使用仿真时间，默认为`true`
- `waypoints` (double[]): 航点列表，格式为`[x, y, z, yaw, ...]`

## 坐标系说明

所有航点坐标都是相对于 **map坐标系**，确保：
1. 小车初始位置在地图原点(0, 0)
2. map → odom 的静态TF已正确发布（在nav.launch.py中已配置）

## 故障排查

### 节点无法启动
- 检查Nav2是否正常运行：`ros2 node list` 应包含 `bt_navigator`
- 确认动作服务器可用：`ros2 action list` 应包含 `/navigate_to_pose`

### 导航不响应
- 检查TF树：`ros2 run tf2_tools view_frames.py`
- 确认map → odom → base_link的完整TF链

### YAML加载失败
- 确认YAML格式正确（使用空格缩进，不使用Tab）
- 检查文件路径是否正确

## 扩展开发

### 添加循环导航

在 `sequential_navigator.cpp` 的 `navigate_to_next_waypoint()` 函数中修改：

```cpp
if (current_waypoint_index_ >= waypoints_.size()) {
    RCLCPP_INFO(this->get_logger(), "一轮导航完成，重新开始");
    current_waypoint_index_ = 0;  // 重置到第一个航点
    navigate_to_next_waypoint();
    return;
}
```

### 添加暂停时间

在到达航点后暂停更长时间，修改延迟时间：

```cpp
timer_ = this->create_wall_timer(
    5s,  // 改为5秒
    [this]() {
        timer_->cancel();
        navigate_to_next_waypoint();
    });
```
