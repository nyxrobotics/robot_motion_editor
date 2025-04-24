import os

import yaml


def save_initial_pose(
        directory,
        joint_names,
        positions,
        enabled,
        pid_config,
        feedback_exprs,
        filename="initial_pose.yaml"):
    """
    Save initial pose and related settings to YAML.
    """
    data = {"joints": {}}
    for name, pos in zip(joint_names, positions):
        data["joints"][name] = {
            "position": float(pos),
            "enable": bool(enabled.get(name, True)),
            "pid": list(pid_config.get(name, (0.0, 0.0, 0.0))),
            "feedback": str(feedback_exprs.get(name, "")).strip()
        }

    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, filename)
    with open(path, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False)


def load_initial_pose(directory, filename="initial_pose.yaml"):
    """
    Load pose and related settings from YAML.
    """
    path = os.path.join(directory, filename)
    if not os.path.exists(path):
        return {}

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    return data.get("joints", {})
