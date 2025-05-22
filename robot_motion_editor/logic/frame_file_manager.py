import os
from dataclasses import dataclass
from dataclasses import field
from typing import Dict
from typing import List

import yaml
from sensor_msgs.msg import JointState


@dataclass
class JointData:
    position: float = 0.0  # in radians
    velocity_scale: float = 1.0
    enable: bool = True
    pid: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    feedback: str = ""


@dataclass
class FrameData:
    move_duration: float = 2.0
    wait_duration: float = 0.0
    joints: Dict[str, JointData] = field(default_factory=dict)
    joint_names: List[str] = field(default_factory=list)

    def set_dict(self, data: dict):
        self.move_duration = data.get("time", {}).get("move_duration", 2.0)
        self.wait_duration = data.get("time", {}).get("wait_duration", 0.0)

        joints_raw = data.get("joints", {})
        velocity_raw = data.get("velocity_scale", {})

        if not self.joint_names:
            self.joint_names = list(joints_raw.keys())

        for name in self.joint_names:
            j = joints_raw.get(name, {})
            vscale = velocity_raw.get(name, 1.0)
            self.joints[name] = JointData(
                position=j.get("position", 0.0),
                velocity_scale=vscale,
                enable=j.get("enable", True),
                pid=j.get("pid", [0.0, 0.0, 0.0]),
                feedback=j.get("feedback", "")
            )

        self.align_data()

    def get_dict(self) -> dict:
        joints_dict = {}
        velocity_scale_dict = {}

        for name, data in self.joints.items():
            joints_dict[name] = {
                "position": data.position,
                "pid": list(data.pid),
                "enable": data.enable,
                "feedback": data.feedback
            }
            velocity_scale_dict[name] = data.velocity_scale

        return {
            "joints": joints_dict,
            "time": {
                "move_duration": self.move_duration,
                "wait_duration": self.wait_duration
            },
            "velocity_scale": velocity_scale_dict
        }

    def set_joint_names(self, joint_names: List[str]):
        self.joint_names = joint_names
        self.align_data()

    def get_joint_names(self) -> List[str]:
        return self.joint_names.copy()

    def align_data(self):
        for name in self.joint_names:
            if name not in self.joints:
                self.joints[name] = JointData()

    def set_pose(self, joint_name: str, position_rad: float):
        self.joints.setdefault(joint_name, JointData()).position = position_rad

    def get_pose(self, joint_name: str) -> float:
        return self.joints.get(joint_name, JointData()).position

    def set_enable(self, joint_name: str, enable: bool):
        self.joints.setdefault(joint_name, JointData()).enable = enable

    def get_enable(self, joint_name: str) -> bool:
        return self.joints.get(joint_name, JointData()).enable

    def set_pid(self, joint_name: str, pid: List[float]):
        self.joints.setdefault(joint_name, JointData()).pid = pid

    def get_pid(self, joint_name: str) -> List[float]:
        return self.joints.get(joint_name, JointData()).pid

    def set_feedback(self, joint_name: str, expr: str):
        self.joints.setdefault(joint_name, JointData()).feedback = expr

    def get_feedback(self, joint_name: str) -> str:
        return self.joints.get(joint_name, JointData()).feedback

    def set_velocity_scale(self, joint_name: str, scale: float):
        self.joints.setdefault(joint_name, JointData()).velocity_scale = scale

    def get_velocity_scale(self, joint_name: str) -> float:
        return self.joints.get(joint_name, JointData()).velocity_scale

    def set_joint_state(self, joint_state_msg: JointState):
        if not self.joint_names:
            self.joint_names = joint_state_msg.name

        for name, pos in zip(joint_state_msg.name, joint_state_msg.position):
            self.set_pose(name, pos)

        self.align_data()

    def get_joint_state(self) -> JointState:
        msg = JointState()
        msg.name = self.joint_names
        msg.position = [self.get_pose(name) for name in self.joint_names]
        return msg


class FrameFileManager:
    @staticmethod
    def save_dict(path: str, data: dict, filename="frame.yaml"):
        os.makedirs(path, exist_ok=True)
        file_path = os.path.join(path, filename)
        try:
            with open(file_path, "w") as f:
                yaml.safe_dump(data, f, default_flow_style=False)
            print(f"[INFO] Frame data saved to: {file_path}")
        except Exception as e:
            print(f"[ERROR] Failed to save frame data to {file_path}: {e}")

    @staticmethod
    def load_dict(path: str, filename="frame.yaml") -> dict:
        file_path = os.path.join(path, filename)
        if not os.path.exists(file_path):
            print(f"[WARN] Frame data file not found: {file_path}")
            return {}
        try:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)
            print(f"[INFO] Frame data loaded from: {file_path}")
            return data or {}
        except Exception as e:
            print(f"[ERROR] Failed to load frame data from {file_path}: {e}")
            return {}

    @staticmethod
    def list_frame_files(folder: str) -> List[str]:
        if not os.path.exists(folder):
            return []
        return [f[:-5] for f in os.listdir(folder) if f.endswith(".yaml")]
