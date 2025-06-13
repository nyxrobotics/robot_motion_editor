import copy
import threading

import rospy
from sensor_msgs.msg import JointState

from .trajectory_visualizer import TrajectoryVisualizer


class InitialPoseVisualizer:
    def __init__(self, joint_names, trajectory_visualizer: TrajectoryVisualizer):
        self.joint_names = joint_names
        self.trajectory_visualizer = trajectory_visualizer
        self.lock = threading.Lock()
        self.start_pose = None
        self.goal_pose = None
        self.duration = 1.0

    def set_duration(self, duration):
        self.duration = duration

    def set_start_pose(self, joint_state_msg):
        with self.lock:
            self.start_pose = joint_state_msg
            if self.goal_pose is None:
                self.goal_pose = joint_state_msg
            self.visualize_goal_state(self.start_pose)

    def set_goal_pose(self, joint_state_msg):
        with self.lock:
            if self.goal_pose is None or joint_state_msg.position != self.goal_pose.position:
                self.goal_pose = joint_state_msg
                if self.start_pose is None:
                    self.start_pose = joint_state_msg
                self.send_state2state(self.start_pose, self.goal_pose)

    def get_goal_pose(self):
        with self.lock:
            return copy.deepcopy(self.goal_pose)

    def visualize_goal_state(self, joint_state):
        self.trajectory_visualizer.visualize_goal_state(joint_state)

    def send_state2state(self, start, end):
        self.trajectory_visualizer.send_state2state(start, end, self.duration)
