import os

import rospy
import yaml
from sensor_msgs.msg import JointState


class InitialPoseFileManager:
    @staticmethod
    def save_dict(filepath, joint_data):
        """
        Save joint initial pose data to a YAML file.

        Parameters:
        - filepath (str): Full path to the YAML file.
        - joint_data (dict): Dictionary formatted as:
            {
                "joint_name_1": {
                    "position": float (radian),
                    "enable": bool,
                    "pid": [P, I, D],
                    "feedback": str
                },
                ...
            }
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        try:
            with open(filepath, "w") as f:
                yaml.safe_dump({"joints": joint_data}, f, default_flow_style=False)
            rospy.loginfo(f"Initial pose successfully saved to: {filepath}")
        except Exception as e:
            rospy.logwarn(f"[ERROR] Failed to save initial pose to: {filepath} — {e}")

    @staticmethod
    def load_dict(filepath):
        """
        Load joint initial pose data from a YAML file.

        Parameters:
        - filepath (str): Full path to the YAML file.

        Returns:
        - dict: joint_data dictionary with same format as described in save_dict()
        """
        if not os.path.exists(filepath):
            rospy.logwarn(f"[InitialPoseFileManager] Initial pose file not found: {filepath}")
            return {}
        try:
            with open(filepath, "r") as f:
                data = yaml.safe_load(f)
            rospy.loginfo(f"[InitialPoseFileManager] Initial pose successfully loaded from: {filepath}")
            return data.get("joints", {})
        except Exception as e:
            rospy.logerr(f"[InitialPoseFileManager] Failed to load initial pose from: {filepath} — {e}")
            return {}


class InitialPoseData:
    """
    A shared in-memory structure for handling initial pose data
    between multiple widgets.

    Provides methods:
    - set_dict(joint_data: dict)
    - get_dict() -> dict
    - set_joint_state(JointState)
    - get_joint_state() -> JointState
    - save_to_file(filepath: str)
    - load_from_file(filepath: str)
    """

    def __init__(self):
        self.data = {}
        self.joint_names = []

    def set_dict(self, joint_data):
        """Set internal joint data from dict."""
        self.data = joint_data.copy()
        if not self.joint_names:  # If joint_names is not set, initialize it from the keys of joint_data
            self.joint_names = list(joint_data.keys())

    def get_dict(self):
        """Get internal joint data as dict."""
        return self.data.copy()

    def set_joint_names(self, joint_names):
        """
        Set the joint names for the internal data structure.
        This is useful for maintaining order when generating JointState messages.
        The existing data is reordered according to the new joint_names.
        """
        self.joint_names = joint_names
        self.align_data()

    def get_joint_names(self):
        """
        Get the joint names in the order they were set.
        This is useful for generating JointState messages.
        """
        return self.joint_names.copy()

    def set_joint_state(self, joint_state_msg):
        """
        Populate internal joint data from JointState message.
        Only 'position' is updated. Other fields remain unchanged.
        If joint_names is not set, it's populated with the order from the message.
        """
        if not self.joint_names:
            self.joint_names = joint_state_msg.name
        for name, pos in zip(joint_state_msg.name, joint_state_msg.position):
            if name in self.data:
                self.data[name]["position"] = pos
            else:
                self.data[name] = {"position": pos}
        self.align_data()

    def get_joint_state(self):
        """
        Generate a JointState message from internal joint data.
        """
        msg = JointState()
        msg.name = self.joint_names
        msg.position = [self.data.get(name, {}).get("position", 0.0) for name in self.joint_names]
        return msg

    def align_data(self):
        """
        Reorder the internal data according to joint_names.
        """
        self.data = {name: self.data.get(name, {"position": 0.0}) for name in self.joint_names}

    def set_pid(self, joint_name: str, pid: "list[float]"):
        self.data.setdefault(joint_name, {})["pid"] = pid

    def get_pid(self, joint_name: str) -> "list[float]":
        return self.data.get(joint_name, {}).get("pid", [0.0, 0.0, 0.0])

    def set_feedback(self, joint_name: str, expr: str):
        self.data.setdefault(joint_name, {})["feedback"] = expr

    def get_feedback(self, joint_name: str) -> str:
        return self.data.get(joint_name, {}).get("feedback", "")

    def set_pose(self, joint_name: str, position_rad: float):
        self.data.setdefault(joint_name, {})["position"] = position_rad

    def get_pose(self, joint_name: str) -> float:
        return self.data.get(joint_name, {}).get("position", 0.0)

    def set_enable(self, joint_name: str, enable: bool):
        self.data.setdefault(joint_name, {})["enable"] = enable

    def get_enable(self, joint_name: str) -> bool:
        return self.data.get(joint_name, {}).get("enable", True)

    def save_to_file(self, filepath: str):
        """
        Save internal joint data to a YAML file using InitialPoseFileManager.
        """
        InitialPoseFileManager.save_dict(filepath, self.get_dict())

    def load_from_file(self, filepath: str):
        """
        Load joint data from a YAML file and update internal state.
        """
        data = InitialPoseFileManager.load_dict(filepath)
        self.set_dict(data)
