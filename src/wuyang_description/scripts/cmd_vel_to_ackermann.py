#!/usr/bin/env python3
"""
Twist(cmd_vel) 转换为 Ackermann 控制器可接受的 Twist(steering angle)。
angular.z: 旋转角速度 → 前轮转向角 = atan(wheelbase * ang_vel / lin_vel)

参数:
  input_topic  (str)  订阅话题，默认 '/cmd_vel'；
                      Nav2 场景下传入 '/cmd_vel_nav'。
  steering_alpha (float) 转向角低通滤波系数，0~1，越小越平滑，默认 0.3
"""
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

WHEELBASE = 0.144


class CmdVelToAckermann(Node):
    def __init__(self):
        super().__init__('cmd_vel_to_ackermann')
        self.declare_parameter('input_topic', '/cmd_vel')
        self.declare_parameter('steering_alpha', 0.3)  # 低通滤波系数
        input_topic = self.get_parameter('input_topic').get_parameter_value().string_value
        self._alpha = self.get_parameter('steering_alpha').get_parameter_value().double_value

        self._steering_filtered = 0.0  # 上一时刻滤波后的转向角

        self.sub = self.create_subscription(
            Twist, input_topic, self.callback, 10
        )
        self.pub = self.create_publisher(
            Twist, '/ackermann_controller/reference_unstamped', 10
        )
        self.get_logger().info(
            f'{input_topic} → /ackermann_controller/reference_unstamped 转换器就绪'
            f'（转向低通滤波 alpha={self._alpha}）'
        )

    def callback(self, msg: Twist):
        out = Twist()
        out.linear.x = msg.linear.x

        # 计算目标转向角
        if abs(msg.linear.x) > 0.01:
            target_steering = math.atan2(
                WHEELBASE * msg.angular.z, msg.linear.x
            )
        else:
            target_steering = 0.0

        # 指数移动平均低通滤波，平滑高频震荡
        self._steering_filtered = (
            self._alpha * target_steering
            + (1.0 - self._alpha) * self._steering_filtered
        )
        out.angular.z = self._steering_filtered
        self.pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = CmdVelToAckermann()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
