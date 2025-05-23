
import os


class MotionDirectoryManager:
    def __init__(self, motion_directory=None):
        self.motion_directory = motion_directory
        self.current_animation_name = None
        self.current_frame_id = None

    # State management
    def set_motion_directory(self, directory: str):
        self.motion_directory = directory

    def set_current_animation(self, animation_name: str):
        self.current_animation_name = animation_name

    def set_current_frame(self, frame_id: str):
        self.current_frame_id = frame_id

    def get_current_animation(self) -> str:
        return self.current_animation_name

    def get_current_frame(self) -> str:
        return self.current_frame_id

    # Path resolution
    def resolve_frame_path(self, frame_name: str) -> str:
        return self._join("frames", f"{frame_name}.yaml")

    def resolve_initial_frame_path(self) -> str:
        return self._join("", "initial_frame.yaml")

    def resolve_animation_file_path(self) -> str:
        return self._join("", "animation.yaml")

    def resolve_if_condition_path(self, condition_name: str) -> str:
        return self._join("conditions/if", f"{condition_name}.yaml")

    def resolve_switch_condition_path(self, condition_name: str) -> str:
        return self._join("conditions/switch", f"{condition_name}.yaml")

    # Listing available files
    def list_animation(self):
        if not self.motion_directory:
            return []
        return [d for d in os.listdir(self.motion_directory)
                if os.path.isdir(os.path.join(self.motion_directory, d))]

    def list_frame(self):
        path = self._join("frames")
        return self._list_yaml_files(path)

    def list_if(self):
        path = self._join("conditions", "if")
        return self._list_yaml_files(path)

    def list_switch(self):
        path = self._join("conditions", "switch")
        return self._list_yaml_files(path)

    def _list_yaml_files(self, path):
        if not os.path.exists(path):
            return []
        return [f[:-5] for f in os.listdir(path) if f.endswith(".yaml")]

    def _join(self, *parts: str) -> str:
        if not self.motion_directory or not self.current_animation_name:
            raise ValueError("motion_directory or current_animation_name is not set.")
        return os.path.join(self.motion_directory, self.current_animation_name, *parts)
