import os

import yaml


def save_if_condition(folder, name, condition_data):
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, f"{name}.yaml")
    with open(filepath, 'w') as f:
        yaml.dump(condition_data, f, sort_keys=False)


def load_if_condition(folder, name):
    filepath = os.path.join(folder, f"{name}.yaml")
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)


def list_if_conditions(folder):
    if not os.path.exists(folder):
        return []
    return [f[:-5] for f in os.listdir(folder) if f.endswith(".yaml")]
