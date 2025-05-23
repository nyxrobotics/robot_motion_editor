import os

import rospy


class MotionDirectoryManager:
    def __init__(self, motion_directory=None):
        self.motion_directory = motion_directory
        self.current_animation_name = None
        self.current_frame_id = None

    def set_current_frame(self, frame_id: str):
        self.current_frame_id = frame_id

    def get_current_frame(self) -> str:
        return self.current_frame_id

    def set_motion_directory(self, directory):
        self.motion_directory = directory

    def get_motion_directory(self):
        return self.motion_directory

    def set_current_animation(self, animation_name):
        self.current_animation_name = animation_name

    def get_current_animation(self):
        return self.current_animation_name

    def get_animation_list(self):
        animations = []
        if not self.motion_directory:
            return animations
        for name in os.listdir(self.motion_directory):
            if os.path.isdir(os.path.join(self.motion_directory, name)):
                animations.append(name)
        return animations

    def resolve_initial_pose_path(self):
        if not self.motion_directory:
            rospy.logerr("motion_directory must be set before resolving paths.")
            return os.path.join("", "initial_pose.yaml")
        return os.path.join(self.motion_directory, "initial_pose.yaml")

    def resolve_animation_path(self):
        return self._join(self.motion_directory, f"{self.current_animation_name}.yaml")

    def resolve_initial_frame_path(self):
        return self._join(self.motion_directory, self.current_animation_name, "initial_frame.yaml")

    def resolve_frame_path(self, frame_name):
        return self._join(self.motion_directory, self.current_animation_name, "frames", f"{frame_name}.yaml")

    def resolve_if_condition_path(self, condition_name):
        return self._join(
            self.motion_directory,
            self.current_animation_name,
            "conditions",
            "if",
            f"{condition_name}.yaml")

    def resolve_switch_condition_path(self, condition_name):
        return self._join(
            self.motion_directory,
            self.current_animation_name,
            "conditions",
            "switch",
            f"{condition_name}.yaml")

    def resolve_animation_yaml_path(self):
        return self._join(self.motion_directory, self.current_animation_name, "animation.yaml")

    def _join(self, *args):
        if not self.motion_directory or not self.current_animation_name:
            rospy.logerr("motion_directory and current_animation_name must be set before resolving paths.")
        return os.path.join(*args)

    # Listing available files
    def list_frame_files(self):
        path = self._join(self.motion_directory, self.current_animation_name, "frames")
        if not os.path.exists(path):
            return []
        return [f[:-5] for f in os.listdir(path) if f.endswith(".yaml")]

    def list_if_condition_files(self):
        path = self._join(self.motion_directory, self.current_animation_name, "conditions", "if")
        if not os.path.exists(path):
            return []
        return [f[:-5] for f in os.listdir(path) if f.endswith(".yaml")]

    def list_switch_condition_files(self):
        path = self._join(self.motion_directory, self.current_animation_name, "conditions", "switch")
        if not os.path.exists(path):
            return []
        return [f[:-5] for f in os.listdir(path) if f.endswith(".yaml")]
