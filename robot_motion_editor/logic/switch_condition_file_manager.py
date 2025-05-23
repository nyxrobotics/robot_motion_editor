import os
from dataclasses import dataclass
from dataclasses import field
from typing import Dict

import yaml


@dataclass
class SwitchConditionData:
    expression: str = ""
    condition: str = ""
    case: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def set_dict(self, data: dict):
        """
        Populate this SwitchConditionData object from a dictionary.
        """
        self.expression = data.get("expression", "")
        self.condition = data.get("condition", "")
        self.case = data.get("case", {}) or {}

    def get_dict(self) -> dict:
        """
        Generate a dictionary from this SwitchConditionData object.
        """
        return {
            "expression": self.expression,
            "condition": self.condition,
            "case": self.case
        }

    def save_to_file(self, filepath: str):
        """
        Save this SwitchConditionData to a YAML file.

        Parameters:
        - filepath (str): Full path to save the YAML file.
        """
        SwitchConditionFileManager.save_dict(filepath, self.get_dict())

    def load_from_file(self, filepath: str):
        """
        Load and update this SwitchConditionData from a YAML file.

        Parameters:
        - filepath (str): Full path to the YAML file to load.
        """
        data = SwitchConditionFileManager.load_dict(filepath)
        self.set_dict(data)


class SwitchConditionFileManager:
    @staticmethod
    def save_dict(filepath: str, data: dict):
        """
        Save switch condition data to a YAML file.

        Parameters:
        - filepath (str): Full file path to save.
        - data (dict): Dictionary to be saved.
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        class SingleQuoted(str):
            pass

        def str_representer(dumper, data):
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style="'")

        yaml.add_representer(SingleQuoted, str_representer)

        quoted_data = dict(data)
        for key in ("expression", "condition"):
            if key in quoted_data and isinstance(quoted_data[key], str):
                quoted_data[key] = SingleQuoted(quoted_data[key])

        try:
            with open(filepath, "w") as f:
                yaml.dump(quoted_data, f, sort_keys=False, allow_unicode=True)
            print(f"[INFO] SwitchCondition saved to: {filepath}")
        except Exception as e:
            print(f"[ERROR] Failed to save SwitchCondition to {filepath}: {e}")

    @staticmethod
    def load_dict(filepath: str) -> dict:
        """
        Load switch condition data from a YAML file.

        Parameters:
        - filepath (str): Full file path to load.

        Returns:
        - dict: Loaded switch condition data.
        """
        if not os.path.exists(filepath):
            print(f"[WARN] SwitchCondition file not found: {filepath}")
            return {}
        try:
            with open(filepath, "r") as f:
                data = yaml.safe_load(f)
            print(f"[INFO] SwitchCondition loaded from: {filepath}")
            return data or {}
        except Exception as e:
            print(f"[ERROR] Failed to load SwitchCondition from {filepath}: {e}")
            return {}
