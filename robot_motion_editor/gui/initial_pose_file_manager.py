import os

import yaml


def save_initial_pose(directory, joint_names, positions, filename="initial_pose.yaml"):
    """
    Save the initial pose to a YAML file.

    :param directory: Target directory to save the file
    :param joint_names: List of joint names
    :param positions: List of joint angles in radians
    :param filename: Output file name (default: initial_pose.yaml)
    """
    data = {"joints": {name: float(pos) for name, pos in zip(joint_names, positions)}}
    os.makedirs(directory, exist_ok=True)

    path = os.path.join(directory, filename)
    with open(path, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False)


def load_initial_pose(directory, filename="initial_pose.yaml"):
    """
    Load the initial pose from a YAML file.

    :param directory: Directory containing the pose file
    :param filename: File name to load (default: initial_pose.yaml)
    :return: Dictionary mapping joint names to angles in radians
    """
    path = os.path.join(directory, filename)
    if not os.path.exists(path):
        return {}

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    return data.get("joints", {})
