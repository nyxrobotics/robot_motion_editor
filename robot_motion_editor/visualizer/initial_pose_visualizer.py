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
        self.current_joint_state = None
        self.last_target = None
        self.duration = 1.0
        # Subscriber
        self.joint_state_sub = rospy.Subscriber("/joint_states", JointState, self.joint_state_callback)

    def set_duration(self, duration):
        self.duration = duration

    def update_joint_state(self, msg):
        with self.lock:
            self.current_joint_state = msg

    def update_target_pose(self, joint_state_msg):
        with self.lock:
            if self.last_target is None or joint_state_msg.position != self.last_target.position:
                self.last_target = copy.deepcopy(joint_state_msg)
                self.trajectory_visualizer.visualize_current2target(
                    self.current_joint_state, self.last_target, self.duration)
                self.trajectory_visualizer.publish_goal_state(self.last_target)

    def get_target_pose(self):
        with self.lock:
            return copy.deepcopy(self.last_target)

    def joint_state_callback(self, msg):
        self.current_joint_state = msg
