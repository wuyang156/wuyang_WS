#include <chrono>
#include <memory>
#include <vector>
#include <cmath>

#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include "nav2_msgs/action/navigate_to_pose.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "tf2/LinearMath/Quaternion.h"
#include "tf2_geometry_msgs/tf2_geometry_msgs.hpp"

using namespace std::chrono_literals;
using NavigateToPose = nav2_msgs::action::NavigateToPose;
using GoalHandleNavigate = rclcpp_action::ClientGoalHandle<NavigateToPose>;

struct Waypoint {
    double x;
    double y;
    double z;
    double yaw;
};

class SequentialNavigator : public rclcpp::Node
{
public:
    SequentialNavigator() : Node("sequential_navigator")
    {
        // 声明参数
        this->declare_parameter<bool>("use_sim_time", true);
        this->declare_parameter<std::vector<double>>("waypoints", std::vector<double>());

        // 创建导航动作客户端
        action_client_ = rclcpp_action::create_client<NavigateToPose>(
            this, "navigate_to_pose");

        // 等待动作服务器
        RCLCPP_INFO(this->get_logger(), "等待导航动作服务器...");
        if (!action_client_->wait_for_action_server(30s)) {
            RCLCPP_ERROR(this->get_logger(), "导航动作服务器未响应！");
            return;
        }
        RCLCPP_INFO(this->get_logger(), "导航动作服务器已连接");

        // 加载航点
        load_waypoints();

        if (waypoints_.empty()) {
            RCLCPP_ERROR(this->get_logger(), "未加载到任何航点！");
            return;
        }

        RCLCPP_INFO(this->get_logger(), "已加载 %zu 个航点", waypoints_.size());

        // 开始导航
        navigate_to_next_waypoint();
    }

private:
    void load_waypoints()
    {
        // 从参数服务器读取航点配置
        // 格式: [x1, y1, z1, yaw1, x2, y2, z2, yaw2, ...]
        std::vector<double> waypoint_params;
        this->get_parameter("waypoints", waypoint_params);

        if (waypoint_params.size() % 4 != 0) {
            RCLCPP_ERROR(this->get_logger(),
                "航点参数格式错误！应为 [x, y, z, yaw] 的倍数");
            return;
        }

        for (size_t i = 0; i < waypoint_params.size(); i += 4) {
            Waypoint wp;
            wp.x = waypoint_params[i];
            wp.y = waypoint_params[i + 1];
            wp.z = waypoint_params[i + 2];
            wp.yaw = waypoint_params[i + 3];
            waypoints_.push_back(wp);

            RCLCPP_INFO(this->get_logger(),
                "航点 %zu: (%.2f, %.2f, %.2f) yaw=%.2f",
                waypoints_.size(), wp.x, wp.y, wp.z, wp.yaw);
        }
    }

    void navigate_to_next_waypoint()
    {
        if (current_waypoint_index_ >= waypoints_.size()) {
            RCLCPP_INFO(this->get_logger(), "所有航点导航完成！");
            return;
        }

        const auto& waypoint = waypoints_[current_waypoint_index_];

        RCLCPP_INFO(this->get_logger(),
            "开始导航到航点 %zu/%zu: (%.2f, %.2f, %.2f) yaw=%.2f",
            current_waypoint_index_ + 1, waypoints_.size(),
            waypoint.x, waypoint.y, waypoint.z, waypoint.yaw);

        // 创建目标姿态
        auto goal_msg = NavigateToPose::Goal();
        goal_msg.pose.header.frame_id = "map";
        goal_msg.pose.header.stamp = this->now();
        goal_msg.pose.pose.position.x = waypoint.x;
        goal_msg.pose.pose.position.y = waypoint.y;
        goal_msg.pose.pose.position.z = waypoint.z;

        // 将yaw角转换为四元数
        tf2::Quaternion q;
        q.setRPY(0.0, 0.0, waypoint.yaw);
        goal_msg.pose.pose.orientation = tf2::toMsg(q);

        // 发送目标
        auto send_goal_options = rclcpp_action::Client<NavigateToPose>::SendGoalOptions();

        send_goal_options.goal_response_callback =
            [this](const GoalHandleNavigate::SharedPtr & goal_handle) {
                if (!goal_handle) {
                    RCLCPP_ERROR(this->get_logger(), "目标被服务器拒绝");
                } else {
                    RCLCPP_INFO(this->get_logger(), "目标已被服务器接受");
                }
            };

        send_goal_options.feedback_callback =
            [this](GoalHandleNavigate::SharedPtr,
                   const std::shared_ptr<const NavigateToPose::Feedback> feedback) {
                // 可以在这里处理反馈信息
                // RCLCPP_INFO(this->get_logger(), "距离目标: %.2f 米",
                //     feedback->distance_remaining);
            };

        send_goal_options.result_callback =
            [this](const GoalHandleNavigate::WrappedResult & result) {
                switch (result.code) {
                    case rclcpp_action::ResultCode::SUCCEEDED:
                        RCLCPP_INFO(this->get_logger(),
                            "航点 %zu 导航成功！", current_waypoint_index_ + 1);
                        current_waypoint_index_++;
                        // 延迟一秒后导航到下一个航点
                        timer_ = this->create_wall_timer(
                            1s, [this]() {
                                timer_->cancel();
                                navigate_to_next_waypoint();
                            });
                        break;
                    case rclcpp_action::ResultCode::ABORTED:
                        RCLCPP_ERROR(this->get_logger(),
                            "航点 %zu 导航被中止", current_waypoint_index_ + 1);
                        break;
                    case rclcpp_action::ResultCode::CANCELED:
                        RCLCPP_WARN(this->get_logger(),
                            "航点 %zu 导航被取消", current_waypoint_index_ + 1);
                        break;
                    default:
                        RCLCPP_ERROR(this->get_logger(),
                            "航点 %zu 导航出现未知错误", current_waypoint_index_ + 1);
                        break;
                }
            };

        action_client_->async_send_goal(goal_msg, send_goal_options);
    }

    rclcpp_action::Client<NavigateToPose>::SharedPtr action_client_;
    std::vector<Waypoint> waypoints_;
    size_t current_waypoint_index_ = 0;
    rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<SequentialNavigator>();
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
