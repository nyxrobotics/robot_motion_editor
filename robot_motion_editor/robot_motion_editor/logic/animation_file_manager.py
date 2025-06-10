import os
from dataclasses import dataclass
from dataclasses import field
from typing import Dict
from typing import List

import yaml


@dataclass
class BlockConnection:
    output: Dict[str, Dict] = field(default_factory=dict)


@dataclass
class BlockInfo:
    type: str = ""
    filename: str = ""
    id: int = 0


@dataclass
class BlockData:
    info: BlockInfo = field(default_factory=BlockInfo)
    place: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    connection: BlockConnection = field(default_factory=BlockConnection)


@dataclass
class ArrowData:
    info: Dict[str, int] = field(default_factory=lambda: {"id": 0})
    waypoints: List[List[float]] = field(default_factory=list)


@dataclass
class AnimationData:
    block: Dict[str, BlockData] = field(default_factory=dict)
    arrow: Dict[str, ArrowData] = field(default_factory=dict)

    def set_dict(self, data: dict):
        """
        Populate internal structures from a dictionary.
        """
        self.block.clear()
        self.arrow.clear()
        raw_block = data.get("block", {})
        raw_arrow = data.get("arrow", {})

        for name, b in raw_block.items():
            info = b.get("info", {})
            place = b.get("place", {})
            conn = b.get("connection", {}).get("output", {})

            block_info = BlockInfo(
                type=info.get("type", ""),
                filename=info.get("filename", ""),
                id=info.get("id", 0)
            )
            self.block[name] = BlockData(
                info=block_info,
                place={
                    "x": place.get("x", 0.0),
                    "y": place.get("y", 0.0)
                },
                connection=BlockConnection(output=conn)
            )

        for name, a in raw_arrow.items():
            self.arrow[name] = ArrowData(
                info=a.get("info", {"id": 0}),
                waypoints=a.get("waypoints", [])
            )

    def get_dict(self) -> dict:
        """
        Generate dictionary representation of the animation data.
        """
        block_dict = {}
        for name, b in self.block.items():
            block_dict[name] = {
                "info": {
                    "type": b.info.type,
                    "filename": b.info.filename,
                    "id": b.info.id
                },
                "place": b.place,
                "connection": {
                    "output": b.connection.output
                }
            }

        arrow_dict = {}
        for name, a in self.arrow.items():
            arrow_dict[name] = {
                "info": a.info,
                "waypoints": a.waypoints
            }

        return {"block": block_dict, "arrow": arrow_dict}

    def save_to_file(self, filepath: str):
        """
        Save the animation data to a YAML file via AnimationFileManager.
        """
        AnimationFileManager.save_dict(filepath, self.get_dict())

    def load_from_file(self, filepath: str):
        """
        Load the animation data from a YAML file using AnimationFileManager.
        """
        data = AnimationFileManager.load_dict(filepath)
        self.set_dict(data)


class AnimationFileManager:
    @staticmethod
    def save_dict(filepath: str, layout_data: dict):
        """
        Save animation layout data to a YAML file.

        Parameters:
        - filepath (str): Full path to YAML file.
        - layout_data (dict): The animation layout as a dictionary.
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        try:
            with open(filepath, 'w') as f:
                yaml.safe_dump({"layout": layout_data}, f, allow_unicode=True)
            print(f"[INFO] Animation saved to: {filepath}")
        except Exception as e:
            print(f"[ERROR] Failed to save animation to {filepath}: {e}")

    @staticmethod
    def load_dict(filepath: str) -> dict:
        """
        Load animation layout data from a YAML file.

        Parameters:
        - filepath (str): Full path to YAML file.

        Returns:
        - dict: Layout dictionary with keys 'block' and 'arrow'
        """
        if not os.path.isfile(filepath):
            print(f"[WARN] Animation file not found: {filepath}")
            return {"block": {}, "arrow": {}}
        try:
            with open(filepath, 'r') as f:
                raw = yaml.safe_load(f)
                return raw.get(
                    "layout", {
                        "block": {}, "arrow": {}}) if isinstance(
                    raw, dict) else {
                    "block": {}, "arrow": {}}
        except Exception as e:
            print(f"[ERROR] Failed to load animation: {e}")
            return {"block": {}, "arrow": {}}
