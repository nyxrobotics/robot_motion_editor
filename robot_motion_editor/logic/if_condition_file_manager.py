import os
from dataclasses import dataclass
from typing import List
from typing import Optional

import yaml


@dataclass
class IfConditionData:
    expression: str = ""
    condition: str = ""

    def set_dict(self, data: dict):
        self.expression = data.get("expression", "")
        self.condition = data.get("condition", "")

    def get_dict(self) -> dict:
        return {
            "expression": self.expression,
            "condition": self.condition
        }


class IfConditionFileManager:
    @staticmethod
    def get_folder_path(project_root: str, animation_name: str) -> str:
        return os.path.join(project_root, animation_name, "conditions", "if")

    @staticmethod
    def get_file_path(project_root: str, animation_name: str, name: str) -> str:
        return os.path.join(IfConditionFileManager.get_folder_path(project_root, animation_name), f"{name}.yaml")

    @staticmethod
    def save_dict(project_root: str, data: dict, name: str = "condition.yaml"):
        folder = os.path.dirname(IfConditionFileManager.get_file_path(project_root, "", name))
        os.makedirs(folder, exist_ok=True)
        file_path = os.path.join(folder, name)
        try:
            with open(file_path, "w") as f:
                yaml.safe_dump(data, f, default_flow_style=False)
            print(f"[INFO] IfCondition data saved to: {file_path}")
        except Exception as e:
            print(f"[ERROR] Failed to save IfCondition data to {file_path}: {e}")

    @staticmethod
    def load_dict(project_root: str, name: str = "condition.yaml") -> dict:
        file_path = IfConditionFileManager.get_file_path(project_root, "", name)
        if not os.path.exists(file_path):
            print(f"[WARN] IfCondition file not found: {file_path}")
            return {}
        try:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)
            print(f"[INFO] IfCondition data loaded from: {file_path}")
            return data or {}
        except Exception as e:
            print(f"[ERROR] Failed to load IfCondition data from {file_path}: {e}")
            return {}

    @staticmethod
    def list_files(project_root: str, animation_name: str) -> List[str]:
        folder = IfConditionFileManager.get_folder_path(project_root, animation_name)
        if not os.path.exists(folder):
            return []
        return [f[:-5] for f in os.listdir(folder) if f.endswith(".yaml")]
