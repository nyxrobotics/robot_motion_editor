import os

import yaml


def load_animation_file(motion_directory, animation_name):
    path = os.path.join(motion_directory, animation_name, "animation.yaml")
    if not os.path.isfile(path):
        return {"block": {}, "arrow": {}}
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
        if isinstance(data, dict):
            layout = data.get("layout")
            if isinstance(layout, dict):
                return layout
            else:
                return {"block": {}, "arrow": {}}
        else:
            return {"block": {}, "arrow": {}}


def save_animation_file(motion_directory, animation_name, layout_data):
    path = os.path.join(motion_directory, animation_name, "animation.yaml")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        yaml.safe_dump({"layout": layout_data}, f, allow_unicode=True)
