import os
from dataclasses import dataclass
from dataclasses import field
from typing import Dict
from typing import List
from typing import Optional

import yaml


@dataclass
class SwitchConditionData:
    expression: str = ""
    condition: str = ""
    case: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def set_dict(self, data: dict):
        self.expression = data.get("expression", "")
        self.condition = data.get("condition", "")
        self.case = data.get("case", {}) or {}

    def get_dict(self) -> dict:
        return {
            "expression": self.expression,
            "condition": self.condition,
            "case": self.case
        }


class SwitchConditionFileManager:
    @staticmethod
    def get_folder_path(project_root: str, animation_name: str) -> str:
        return os.path.join(project_root, animation_name, "conditions", "switch")

    @staticmethod
    def get_file_path(project_root: str, animation_name: str, name: str) -> str:
        return os.path.join(SwitchConditionFileManager.get_folder_path(project_root, animation_name), f"{name}.yaml")

    @staticmethod
    def save_dict(path: str, data: dict, filename="condition.yaml"):
        os.makedirs(path, exist_ok=True)
        file_path = os.path.join(path, filename)

        class SingleQuoted(str):
            pass

        def str_representer(dumper, data):
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style="'")

        yaml.add_representer(SingleQuoted, str_representer)

        # 特定のフィールドにシングルクォートを適用
        quoted_data = dict(data)
        for key in ("expression", "condition"):
            if key in quoted_data and isinstance(quoted_data[key], str):
                quoted_data[key] = SingleQuoted(quoted_data[key])

        try:
            with open(file_path, "w") as f:
                yaml.dump(quoted_data, f, sort_keys=False, allow_unicode=True)
            print(f"[INFO] SwitchCondition saved to: {file_path}")
        except Exception as e:
            print(f"[ERROR] Failed to save SwitchCondition to {file_path}: {e}")

    @staticmethod
    def load_dict(project_root: str, name: str = "condition.yaml") -> dict:
        file_path = os.path.join(project_root, name)
        if not os.path.exists(file_path):
            print(f"[WARN] SwitchCondition file not found: {file_path}")
            return {}
        try:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)
            print(f"[INFO] SwitchCondition loaded from: {file_path}")
            return data or {}
        except Exception as e:
            print(f"[ERROR] Failed to load SwitchCondition from {file_path}: {e}")
            return {}

    @staticmethod
    def list_files(project_root: str, animation_name: str) -> List[str]:
        folder = SwitchConditionFileManager.get_folder_path(project_root, animation_name)
        if not os.path.exists(folder):
            return []
        return [f[:-5] for f in os.listdir(folder) if f.endswith(".yaml")]
