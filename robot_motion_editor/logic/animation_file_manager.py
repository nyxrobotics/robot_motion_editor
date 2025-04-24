import os

import yaml


def load_animation_file(filepath):
    if not os.path.exists(filepath):
        return {}, [], [], []

    with open(filepath, 'r') as f:
        data = yaml.safe_load(f) or {}

    layout = data.get("layout", {})
    connections = data.get("connections", [])
    if_conditions = data.get("if_conditions", [])
    switch_conditions = data.get("switch_conditions", [])

    return layout, connections, if_conditions, switch_conditions


def save_animation_file(filepath, layout, connections, if_conditions, switch_conditions):
    data = {
        "layout": layout,
        "connections": connections,
        "if_conditions": if_conditions,
        "switch_conditions": switch_conditions,
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


def create_if_condition(from_frame, condition, to_true, to_false):
    return {
        "from": from_frame,
        "condition": condition,
        "to_true": to_true,
        "to_false": to_false
    }


def create_switch_condition(from_frame, variable, cases):
    return {
        "from": from_frame,
        "variable": variable,
        "cases": cases
    }
