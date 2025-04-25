import os

import yaml


def save_switch_condition(project_root, animation_name, name, condition_data):
    folder = os.path.join(project_root, animation_name, "conditions", "switch")
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, f"{name}.yaml")
    with open(filepath, 'w') as f:
        yaml.dump(condition_data, f, sort_keys=False)


def load_switch_condition(project_root, animation_name, name):
    filepath = os.path.join(project_root, animation_name, "conditions", "switch", f"{name}.yaml")
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)


def list_switch_conditions(project_root, animation_name):
    folder = os.path.join(project_root, animation_name, "conditions", "switch")
    if not os.path.exists(folder):
        return []
    return [f[:-5] for f in os.listdir(folder) if f.endswith(".yaml")]
