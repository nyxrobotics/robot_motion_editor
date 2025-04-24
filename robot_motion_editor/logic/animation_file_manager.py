import os

import yaml

from .frame_file_manager import list_frame_files
from .frame_file_manager import load_frame_file
from .frame_file_manager import save_frame_file
from .if_condition_file_manager import load_if_condition
from .if_condition_file_manager import save_if_condition
from .switch_condition_file_manager import load_switch_condition
from .switch_condition_file_manager import save_switch_condition


def load_animation_file(filepath):
    if not os.path.exists(filepath):
        return {}, [], [], []

    with open(filepath, 'r') as f:
        data = yaml.safe_load(f) or {}

    layout = data.get("layout", {})
    connections = data.get("connections", [])
    if_conditions_refs = data.get("if_conditions", [])
    switch_conditions_refs = data.get("switch_conditions", [])

    animation_dir = os.path.dirname(filepath)
    conditions_dir = os.path.join(animation_dir, "conditions")

    if_conditions = []
    for ref in if_conditions_refs:
        name = ref.get("name")
        if not name:
            continue
        cond_data = load_if_condition(conditions_dir, name)
        if cond_data:
            cond_data["name"] = name
            if_conditions.append(cond_data)

    switch_conditions = []
    for ref in switch_conditions_refs:
        name = ref.get("name")
        if not name:
            continue
        cond_data = load_switch_condition(conditions_dir, name)
        if cond_data:
            cond_data["name"] = name
            switch_conditions.append(cond_data)

    return layout, connections, if_conditions, switch_conditions


def save_animation_file(filepath, layout, connections, if_conditions, switch_conditions, frame_data_map=None):
    animation_dir = os.path.dirname(filepath)
    conditions_dir = os.path.join(animation_dir, "conditions")
    frames_dir = os.path.join(animation_dir, "frames")
    os.makedirs(conditions_dir, exist_ok=True)
    os.makedirs(frames_dir, exist_ok=True)

    if_condition_refs = []
    for cond in if_conditions:
        name = cond.get("name")
        if not name:
            continue
        save_if_condition(conditions_dir, name, {k: v for k, v in cond.items() if k != "name"})
        if_condition_refs.append({"name": name})

    switch_condition_refs = []
    for cond in switch_conditions:
        name = cond.get("name")
        if not name:
            continue
        save_switch_condition(conditions_dir, name, {k: v for k, v in cond.items() if k != "name"})
        switch_condition_refs.append({"name": name})

    # Save frames if provided
    if frame_data_map:
        for name, data in frame_data_map.items():
            frame_path = os.path.join(frames_dir, f"{name}.yaml")
            save_frame_file(frame_path, data)

    data = {
        "layout": layout,
        "connections": connections,
        "if_conditions": if_condition_refs,
        "switch_conditions": switch_condition_refs
    }

    with open(filepath, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def prune_invalid_entries(layout, connections, if_conditions, switch_conditions, available_frames):
    layout = {k: v for k, v in layout.items() if k in available_frames}

    def valid_frame(f):
        return f in available_frames

    connections = [c for c in connections if valid_frame(c['from']) and valid_frame(c['to'])]

    if_conditions = [c for c in if_conditions if valid_frame(c['from'])
                     and valid_frame(c['to_true']) and valid_frame(c['to_false'])]

    def switch_valid(c):
        if not valid_frame(c['from']):
            return False
        for dest in c['cases'].values():
            if not valid_frame(dest):
                return False
        return True

    switch_conditions = [c for c in switch_conditions if switch_valid(c)]

    return layout, connections, if_conditions, switch_conditions


def create_empty_animation():
    return {
        "layout": {},
        "connections": [],
        "if_conditions": [],
        "switch_conditions": []
    }


def create_connection(from_frame, to_frame, waypoints=None):
    conn = {"from": from_frame, "to": to_frame}
    if waypoints:
        conn["waypoints"] = waypoints
    return conn


def create_if_condition(name, from_frame, condition, to_true, to_false):
    return {
        "name": name,
        "from": from_frame,
        "condition": condition,
        "to_true": to_true,
        "to_false": to_false
    }


def create_switch_condition(name, from_frame, variable, cases):
    return {
        "name": name,
        "from": from_frame,
        "variable": variable,
        "cases": cases
    }
