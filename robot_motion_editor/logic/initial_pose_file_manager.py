
import os

import rospy
import yaml


def save_initial_pose(path, joint_data, filename="initial_pose.yaml"):
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
            "joint_name_2": { ... },
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


def load_initial_pose(path, filename="initial_pose.yaml"):
    """
    Load joint initial pose data from a YAML file.

    Parameters:
    - path (str): Directory containing the YAML file.
    - filename (str): YAML filename (default: "initial_pose.yaml")

    Returns:
    - dict: joint_data dictionary with same format as described in save_initial_pose()
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
