import os

import yaml


def load_frame_file(filepath):
    if not os.path.exists(filepath):
        return {}
    with open(filepath, 'r') as f:
        return yaml.safe_load(f) or {}


def save_frame_file(filepath, data):
    with open(filepath, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def create_default_frame():
    return {
        "joints": {
            # "joint1": {
            #     "position": 0.0,
            #     "speed": 1.0,
            #     "enable": True,
            #     "pid": [0.0, 0.0, 0.0],
            #     "feedback": ""
            # }
        },
        "time": {
            # "duration": 1.0,
            # "wait": 0.0
        },
        "velocity_scale": {
            # "joint1": 1.0
        }
    }


def list_frame_files(folder):
    if not os.path.exists(folder):
        return []
    return [f[:-5] for f in os.listdir(folder) if f.endswith(".yaml")]
