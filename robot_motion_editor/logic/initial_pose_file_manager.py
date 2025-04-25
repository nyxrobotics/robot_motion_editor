import os

import yaml


def save_initial_pose(
        project_root,
        joint_names,
        positions,
        enabled,
        pid_config,
        feedback_exprs,
        filename="initial_pose.yaml"):
    """
    Save initial pose and related settings to YAML under <project_root>/initial_pose.yaml.
    """
    data = {"joints": {}}
    for name, pos in zip(joint_names, positions):
        data["joints"][name] = {
            "position": float(pos),
            "enable": bool(enabled.get(name, True)),
            "pid": list(pid_config.get(name, (0.0, 0.0, 0.0))),
            "feedback": str(feedback_exprs.get(name, "")).strip()
        }

    os.makedirs(project_root, exist_ok=True)
    path = os.path.join(project_root, filename)
    with open(path, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False)


def load_initial_pose(project_root, filename="initial_pose.yaml"):
    """
    Load pose and related settings from <project_root>/initial_pose.yaml.
    """
    path = os.path.join(project_root, filename)
    if not os.path.exists(path):
        return {}

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    return data.get("joints", {})
