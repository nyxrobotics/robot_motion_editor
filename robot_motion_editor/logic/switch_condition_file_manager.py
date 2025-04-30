import os

import yaml


def save_switch_condition(project_root, animation_name, name, condition_data):
    folder = os.path.join(project_root, animation_name, "conditions", "switch")
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, f"{name}.yaml")

    # YAMLのDumperに任せてシングルクォートで自動出力（安全）
    class SingleQuoted(str):
        pass

    def str_representer(dumper, data):
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style="'")

    yaml.add_representer(SingleQuoted, str_representer)

    data = dict(condition_data)
    for key in ("expression", "condition"):
        if key in data and isinstance(data[key], str):
            data[key] = SingleQuoted(data[key])

    with open(filepath, 'w') as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True)


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
