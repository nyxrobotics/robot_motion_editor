import os
from dataclasses import dataclass

import yaml


@dataclass
class IfConditionData:
    expression: str = ""
    condition: str = ""

    def set_dict(self, data: dict):
        """
        Populate this IfConditionData object from a dictionary.
        """
        self.expression = data.get("expression", "")
        self.condition = data.get("condition", "")

    def get_dict(self) -> dict:
        """
        Generate a dictionary from this IfConditionData object.
        """
        return {
            "expression": self.expression,
            "condition": self.condition
        }

    def save_to_file(self, filepath: str):
        """
        Save this IfConditionData to a YAML file.

        Parameters:
        - filepath (str): Full path to save the YAML file.
        """
        IfConditionFileManager.save_dict(filepath, self.get_dict())

    def load_from_file(self, filepath: str):
        """
        Load and update this IfConditionData from a YAML file.

        Parameters:
        - filepath (str): Full path to the YAML file to load.
        """
        data = IfConditionFileManager.load_dict(filepath)
        self.set_dict(data)


class IfConditionFileManager:
    @staticmethod
    def save_dict(filepath: str, data: dict):
        """
        Save condition data to a YAML file.

        Parameters:
        - filepath (str): Full file path to save.
        - data (dict): Dictionary to be saved.
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        try:
            with open(filepath, "w") as f:
                yaml.safe_dump(data, f, default_flow_style=False)
            print(f"[INFO] IfCondition data saved to: {filepath}")
        except Exception as e:
            print(f"[ERROR] Failed to save IfCondition data to {filepath}: {e}")

    @staticmethod
    def load_dict(filepath: str) -> dict:
        """
        Load condition data from a YAML file.

        Parameters:
        - filepath (str): Full file path to load.

        Returns:
        - dict: Loaded condition data.
        """
        if not os.path.exists(filepath):
            print(f"[WARN] IfCondition file not found: {filepath}")
            return {}
        try:
            with open(filepath, "r") as f:
                data = yaml.safe_load(f)
            print(f"[INFO] IfCondition data loaded from: {filepath}")
            return data or {}
        except Exception as e:
            print(f"[ERROR] Failed to load IfCondition data from {filepath}: {e}")
            return {}
