cmake_minimum_required(VERSION 3.8)
project(wuyang_description)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)

# cmd_vel → ackermann 桥接节点（C++）
add_executable(cmd_vel_bridge src/cmd_vel_bridge.cpp)
ament_target_dependencies(cmd_vel_bridge rclcpp geometry_msgs)
install(TARGETS cmd_vel_bridge DESTINATION lib/${PROJECT_NAME})

install(
  DIRECTORY urdf launch config world maps rviz2
  DESTINATION share/${PROJECT_NAME}
)

# Python 脚本保留供 Nav2 场景复用
install(PROGRAMS
  scripts/cmd_vel_to_ackermann.py
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  set(ament_cmake_copyright_FOUND TRUE)
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
