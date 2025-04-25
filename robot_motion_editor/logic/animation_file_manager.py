import os

import yaml

from .frame_file_manager import save_frame_file
from .if_condition_file_manager import save_if_condition
from .switch_condition_file_manager import save_switch_condition


def create_empty_animation():
    return {"layout": {"block": {}, "arrow": {}}}


def load_animation_file(project_root, animation_name):
    filepath = os.path.join(project_root, animation_name, "animation.yaml")
    if not os.path.exists(filepath):
        return {"layout": {"block": {}, "arrow": {}}}

    with open(filepath, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}

    layout = data.get("layout", {"block": {}, "arrow": {}})
    return {"layout": layout}


def save_animation_file(project_root, animation_name, layout, frame_data_map=None):
    animation_dir = os.path.join(project_root, animation_name)
    os.makedirs(animation_dir, exist_ok=True)
    frames_dir = os.path.join(animation_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)

    if frame_data_map:
        for name, data in frame_data_map.items():
            frame_path = os.path.join(frames_dir, f"{name}.yaml")
            save_frame_file(frame_path, data)

    animation_path = os.path.join(animation_dir, "animation.yaml")
    print("[DEBUG] Writing to file:", animation_path)
    print("[DEBUG] Layout content:", layout)

    data = {"layout": layout}
    with open(animation_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def prune_invalid_entries(layout, available_frames):
    def valid_frame(fid):
        return fid in available_frames

    filtered_layout = {
        k: v for k, v in layout.items()
        if (v.get("type") == "frame" and v.get("file_name") in available_frames)
        or (v.get("type") in ("if_condition", "switch_condition") and v.get("name"))
    }

    return filtered_layout
