
import os

import rospy
import yaml
from sensor_msgs.msg import JointState


class InitialPoseFileManager:
    def save_dict(path, joint_data, filename="initial_pose.yaml"):
        """
        Save joint initial pose data to a YAML file.

        Parameters:
        - path (str): Directory to save the file.
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
        - filename (str): YAML filename (default: "initial_pose.yaml")
        """
        os.makedirs(path, exist_ok=True)
        file_path = os.path.abspath(os.path.join(path, filename))
        try:
            with open(file_path, "w") as f:
                yaml.safe_dump({"joints": joint_data}, f, default_flow_style=False)
            rospy.loginfo(f"Initial pose successfully saved to: {file_path}")
        except Exception as e:
            rospy.logwarn(f"[ERROR] Failed to save initial pose to: {file_path} — {e}")

    def load_dict(path, filename="initial_pose.yaml"):
        """
        Load joint initial pose data from a YAML file.

        Parameters:
        - path (str): Directory containing the YAML file.
        - filename (str): YAML filename (default: "initial_pose.yaml")

        Returns:
        - dict: joint_data dictionary with same format as described in save_dict()
        """
        file_path = os.path.abspath(os.path.join(path, filename))
        if not os.path.exists(file_path):
            rospy.logwarn(f"[WARN] Initial pose file not found: {file_path}")
            return {}
        try:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)
            rospy.loginfo(f"Initial pose successfully loaded from: {file_path}")
            return data.get("joints", {})
        except Exception as e:
            rospy.logwarn(f"[ERROR] Failed to load initial pose from: {file_path} — {e}")
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
        if not self.joint_names:  # If joint_names is not set, initialize it from the order in joint_state_msg
            self.joint_names = joint_state_msg.name

        for name, pos in zip(joint_state_msg.name, joint_state_msg.position):
            if name in self.data:
                self.data[name]["position"] = pos
            else:
                self.data[name] = {"position": pos}

        # After setting the state, reorder data if needed
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
