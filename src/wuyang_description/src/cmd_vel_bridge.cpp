#include <cmath>
#include <string>
#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist.hpp"

static constexpr double WHEELBASE = 0.144;  // 轴距 (m)

class CmdVelBridge : public rclcpp::Node
{
public:
  CmdVelBridge() : Node("cmd_vel_bridge")
  {
    this->declare_parameter<std::string>("input_topic", "/cmd_vel");
    auto input_topic = this->get_parameter("input_topic").as_string();

    sub_ = this->create_subscription<geometry_msgs::msg::Twist>(
      input_topic, 10,
      std::bind(&CmdVelBridge::callback, this, std::placeholders::_1));

    pub_ = this->create_publisher<geometry_msgs::msg::Twist>(
      "/ackermann_controller/reference_unstamped", 10);

    RCLCPP_INFO(this->get_logger(),
      "%s → /ackermann_controller/reference_unstamped 桥接节点就绪",
      input_topic.c_str());
  }

private:
  // angular.z (角速度) → 前轮转向角 = atan(L * ω / v)
  void callback(const geometry_msgs::msg::Twist::SharedPtr msg)
  {
    geometry_msgs::msg::Twist out;
    out.linear.x = msg->linear.x;
    if (std::abs(msg->linear.x) > 0.01) {
      out.angular.z = std::atan2(WHEELBASE * msg->angular.z, msg->linear.x);
    } else {
      out.angular.z = 0.0;
    }
    pub_->publish(out);
  }

  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr sub_;
  rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr pub_;
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<CmdVelBridge>());
  rclcpp::shutdown();
  return 0;
}
