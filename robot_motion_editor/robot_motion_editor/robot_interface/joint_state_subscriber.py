import threading
from typing import Union

import rospy
from sensor_msgs.msg import JointState


class JointStateSubscriber:
    def __init__(self, topic="/joint_states", joint_names: list = None):
        self._lock = threading.Lock()
        self.joint_names = joint_names
        self._joint_state = None
        self._subscriber = rospy.Subscriber(topic, JointState, self._callback)
        rospy.loginfo(f"[JointStateSubscriber] Subscribed to {topic}")

    def _callback(self, msg):
        with self._lock:
            self._joint_state = msg

    def get_joint_state(self):
        with self._lock:
            return self._alignjoint_states(self._joint_state, self.joint_names)

    def reset_joint_state(self):
        with self._lock:
            self._joint_state = None

    def wait_for_joint_state(self, timeout=5.0):
        start_time = rospy.Time.now()
        timeout_duration = rospy.Duration(timeout)
        self.reset_joint_state
        while rospy.Time.now() - start_time < timeout_duration:
            if self._joint_state is not None:
                with self._lock:
                    return self._alignjoint_states(self._joint_state, self.joint_names)
            rospy.sleep(0.1)
        return None

    def _alignjoint_states(self, source: JointState, reference: Union[JointState, list, None]) -> JointState:
        # If reference is None, return the source JointState as-is
        if reference is None:
            return source

        # Get the list of reference joint names
        ref_names = reference.name if isinstance(reference, JointState) else reference

        # Create a dictionary mapping joint names to positions from the source JointState
        source_dict = dict(zip(source.name, source.position))

        # Build a position list aligned to the reference joint names
        aligned_positions = []
        for name in ref_names:
            if name in source_dict:
                aligned_positions.append(source_dict[name])
            else:
                aligned_positions.append(0.0)  # Default position if the joint is missing in source

        # Create a new JointState message with aligned data
        aligned_joint_state = JointState()
        aligned_joint_state.header = source.header  # Copy header from source
        aligned_joint_state.name = list(ref_names)
        aligned_joint_state.position = aligned_positions

        # velocity and effort can also be aligned here if necessary
        return aligned_joint_state
