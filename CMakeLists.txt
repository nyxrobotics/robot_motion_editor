cmake_minimum_required(VERSION 3.0.2)
project(robot_motion_editor)

find_package(
  catkin REQUIRED
  COMPONENTS rospy
             std_msgs
             sensor_msgs
             trajectory_msgs
             urdf
)

catkin_python_setup()

catkin_package()

include_directories(${catkin_INCLUDE_DIRS})
