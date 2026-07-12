// cmd_vel_interceptor.cpp
//
// 功能：订阅 Nav2 输出的 /origin_cmd 与感知节点的 /visual_result，
//       根据视觉标志位对速度做平滑限制后发布到 /cmd_vel 控制小车。
//
// 标志位含义：
//   0 - 正常，直接透传
//   1 - 红灯，平滑停车
//   2 - 慢行，降速至 slow_ratio 倍
//   3 - 行人，平滑停车
//   4 - 停车，平滑停车
//
// 平滑减速：每个定时器 tick 对输出速度施加最大加速度约束，
//           避免速度突变导致里程计积分误差。

#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/twist.hpp>
#include <std_msgs/msg/int32.hpp>
#include <cmath>

// ────────────────────────────────────────────────────────────────
// 视觉标志枚举
// ────────────────────────────────────────────────────────────────
enum class VisualFlag : int
{
  NORMAL     = 0,
  RED_LIGHT  = 1,
  SLOW       = 2,
  PEDESTRIAN = 3,
  STOP       = 4,
};

// ────────────────────────────────────────────────────────────────
// 拦截节点
// ────────────────────────────────────────────────────────────────
class CmdVelInterceptor : public rclcpp::Node
{
public:
  CmdVelInterceptor()
  : Node("cmd_vel_interceptor"),
    visual_flag_(static_cast<int>(VisualFlag::NORMAL)),
    cur_vx_(0.0),
    cur_wz_(0.0)
  {
    // ── 参数声明 ──────────────────────────────────────────────
    // 与 controller_server 频率保持一致（30 Hz）
    declare_parameter("publish_rate",   30.0);  // Hz
    // 线速度最大减速度（m/s²），0.5 m/s 速度约 1 s 停稳
    declare_parameter("max_decel",       0.5);  // m/s²
    // 角速度最大减速度（rad/s²）
    declare_parameter("max_ang_decel",   1.0);  // rad/s²
    // SLOW 模式速度倍率，0.4 表示降至正常速度的 40%
    declare_parameter("slow_ratio",      0.4);
    // /visual_result 超时时间（秒），超时后当作 NORMAL 处理
    declare_parameter("visual_timeout",  1.0);  // s

    publish_rate_   = get_parameter("publish_rate").as_double();
    max_decel_      = get_parameter("max_decel").as_double();
    max_ang_decel_  = get_parameter("max_ang_decel").as_double();
    slow_ratio_     = get_parameter("slow_ratio").as_double();
    visual_timeout_ = get_parameter("visual_timeout").as_double();

    // 每个 tick 允许的最大速度变化量
    double dt  = 1.0 / publish_rate_;
    max_dvx_   = max_decel_     * dt;
    max_dwz_   = max_ang_decel_ * dt;

    // ── 订阅 ──────────────────────────────────────────────────
    // Nav2 controller_server 输出（cmd_vel_topic 已改为 /origin_cmd）
    origin_sub_ = create_subscription<geometry_msgs::msg::Twist>(
      "/origin_cmd", 10,
      [this](const geometry_msgs::msg::Twist::SharedPtr msg) {
        origin_cmd_ = *msg;
      });

    // 感知节点输出（0~4 标志位）
    visual_sub_ = create_subscription<std_msgs::msg::Int32>(
      "/visual_result", 10,
      [this](const std_msgs::msg::Int32::SharedPtr msg) {
        visual_flag_      = msg->data;
        last_visual_time_ = now();
      });

    // ── 发布 ──────────────────────────────────────────────────
    cmd_pub_ = create_publisher<geometry_msgs::msg::Twist>("/cmd_vel", 10);

    // ── 定时器 ────────────────────────────────────────────────
    using namespace std::chrono;
    auto period = duration_cast<nanoseconds>(duration<double>(dt));
    timer_ = create_wall_timer(
      period, std::bind(&CmdVelInterceptor::timerCallback, this));

    // 初始化时间戳，避免首次超时误判
    last_visual_time_ = now();

    RCLCPP_INFO(get_logger(),
      "cmd_vel_interceptor 已启动  /origin_cmd + /visual_result → /cmd_vel"
      "  (max_decel=%.2f m/s², slow_ratio=%.2f)",
      max_decel_, slow_ratio_);
  }

private:
  // ── 平滑斜坡函数 ──────────────────────────────────────────────
  /// 将 current 朝 target 方向移动，单步最大变化量为 max_delta。
  static double ramp(double current, double target, double max_delta)
  {
    double diff = target - current;
    if (std::abs(diff) <= max_delta) {
      return target;
    }
    return current + std::copysign(max_delta, diff);
  }

  // ── 定时器回调 ────────────────────────────────────────────────
  void timerCallback()
  {
    // 若 /visual_result 长时间未更新，退回 NORMAL 以保证导航不中断
    int flag = visual_flag_;
    if ((now() - last_visual_time_).seconds() > visual_timeout_) {
      flag = static_cast<int>(VisualFlag::NORMAL);
    }

    // 根据标志位计算目标速度
    double target_vx = 0.0;
    double target_wz = 0.0;

    switch (static_cast<VisualFlag>(flag)) {
      case VisualFlag::NORMAL:
        // 路况正常：直接跟随 Nav2 指令
        target_vx = origin_cmd_.linear.x;
        target_wz = origin_cmd_.angular.z;
        break;

      case VisualFlag::RED_LIGHT:
        // 红灯：停车等待
        target_vx = 0.0;
        target_wz = 0.0;
        break;

      case VisualFlag::SLOW:
        // 慢行：按比例降速，保留角速度分量使转向不失控
        target_vx = origin_cmd_.linear.x  * slow_ratio_;
        target_wz = origin_cmd_.angular.z * slow_ratio_;
        break;

      case VisualFlag::PEDESTRIAN:
        // 行人：停车等待
        target_vx = 0.0;
        target_wz = 0.0;
        break;

      case VisualFlag::STOP:
        // 停车指令
        target_vx = 0.0;
        target_wz = 0.0;
        break;

      default:
        RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 3000,
          "未知 visual_flag=%d，按 NORMAL 处理", flag);
        target_vx = origin_cmd_.linear.x;
        target_wz = origin_cmd_.angular.z;
        break;
    }

    // 施加速度斜坡，避免速度突变
    cur_vx_ = ramp(cur_vx_, target_vx, max_dvx_);
    cur_wz_ = ramp(cur_wz_, target_wz, max_dwz_);

    // 发布到小车底盘
    geometry_msgs::msg::Twist out;
    out.linear.x  = cur_vx_;
    out.angular.z = cur_wz_;
    cmd_pub_->publish(out);
  }

  // ── 成员变量 ──────────────────────────────────────────────────
  // 参数
  double publish_rate_;
  double max_decel_;
  double max_ang_decel_;
  double slow_ratio_;
  double visual_timeout_;
  double max_dvx_;   // 每个 tick 线速度最大变化量
  double max_dwz_;   // 每个 tick 角速度最大变化量

  // 运行状态
  geometry_msgs::msg::Twist origin_cmd_;  // Nav2 最新指令
  int                       visual_flag_; // 感知最新标志
  double                    cur_vx_;      // 当前输出线速度（已平滑）
  double                    cur_wz_;      // 当前输出角速度（已平滑）
  rclcpp::Time              last_visual_time_;

  // ROS 接口
  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr origin_sub_;
  rclcpp::Subscription<std_msgs::msg::Int32>::SharedPtr       visual_sub_;
  rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr     cmd_pub_;
  rclcpp::TimerBase::SharedPtr                                timer_;
};

// ────────────────────────────────────────────────────────────────
int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<CmdVelInterceptor>());
  rclcpp::shutdown();
  return 0;
}
