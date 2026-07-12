cmake_minimum_required(VERSION 3.5)
project(wheeltec_wuyang_nav2)

if(NOT CMAKE_C_STANDARD)
  set(CMAKE_C_STANDARD 99)
endif()
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(nav2_bringup REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav2_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)

# 顺序导航节点
add_executable(sequential_navigator src/sequential_navigator.cpp)
ament_target_dependencies(sequential_navigator
  rclcpp
  rclcpp_action
  geometry_msgs
  nav2_msgs
  tf2
  tf2_geometry_msgs
)
install(TARGETS sequential_navigator
  DESTINATION lib/${PROJECT_NAME}
)

################################################################################
# Install
################################################################################
install(
  DIRECTORY launch map param rviz config
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  set(ament_cmake_copyright_FOUND TRUE)
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
