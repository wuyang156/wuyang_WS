#!/usr/bin/env python3
"""
将 geometry_msgs/Twist 转换为 ackermann_msgs/AckermannDrive，
使得 teleop_twist_keyboard 可以控制阿克曼小车。
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from ackermann_msgs.msg import AckermannDrive


class TwistToAckermann(Node):
    def __init__(self):
        super().__init__('twist_to_ackermann')
        self.sub = self.create_subscription(
            Twist, '/cmd_vel', self.callback, 10
        )
        self.pub = self.create_publisher(
            AckermannDrive, '/ackermann_controller/reference', 10
        )
        self.get_logger().info('Twist to Ackermann converter started')

    def callback(self, msg: Twist):
        ack = AckermannDrive()
        ack.speed = msg.linear.x
        ack.steering_angle = msg.angular.z
        self.pub.publish(ack)


def main(args=None):
    rclpy.init(args=args)
    node = TwistToAckermann()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
