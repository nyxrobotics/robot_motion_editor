import os

import rospy

from .frame_file_manager import FrameData
from .if_condition_file_manager import IfConditionData
from .switch_condition_file_manager import SwitchConditionData


class MotionDirectoryManager:
    def __init__(self, motion_directory=None, joint_names=None):
        # File manager
        self.motion_directory = motion_directory
        self.current_animation_name = None
        self.current_frame_id = None
        self.joint_names = joint_names or []
        # Data buffer
        self.frames = {}
        self.ifs = {}
        self.switches = {}
        self.initial_frame = None

    def set_joint_names(self, joint_names):
        self.joint_names = joint_names

    def get_joint_names(self):
        return self.joint_names

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

    def resolve_animation_path(self, name=None):
        anim_name = name or self.current_animation_name
        if not self.motion_directory or not anim_name:
            rospy.logerr("motion_directory and animation name must be set before resolving paths.")
            return None
        return self._join(self.motion_directory, anim_name)

    def resolve_initial_frame_path(self):
        return self._join(self.motion_directory, self.current_animation_name, "initial_frame.yaml")

    def resolve_frame_path(self, frame_name):
        if frame_name is None:
            rospy.logerr("Frame name must be provided to resolve path.")
            return None
        return self._join(self.motion_directory, self.current_animation_name, "frames", f"{frame_name}.yaml")

    def resolve_if_condition_path(self, filename):
        if filename is None:
            rospy.logerr("Condition name must be provided to resolve path.")
            return None
        return self._join(
            self.motion_directory,
            self.current_animation_name,
            "conditions",
            "if",
            f"{filename}.yaml")

    def resolve_switch_condition_path(self, filename):
        if filename is None:
            rospy.logerr("Condition name must be provided to resolve path.")
            return None
        return self._join(
            self.motion_directory,
            self.current_animation_name,
            "conditions",
            "switch",
            f"{filename}.yaml")

    def resolve_animation_yaml_path(self):
        return self._join(self.motion_directory, self.current_animation_name, "animation.yaml")

    def _join(self, *args):
        if not self.motion_directory or not self.current_animation_name:
            rospy.logerr("motion_directory and current_animation_name must be set before resolving paths.")
        return os.path.join(*args)

    # Listing available files
    def list_animation(self):
        """Returns all animation names in the motion directory (for which animation.yaml exists)"""
        animations = []
        if not self.motion_directory:
            rospy.logwarn("motion_directory is not set.")
            return animations

        for name in os.listdir(self.motion_directory):
            dir_path = os.path.join(self.motion_directory, name)
            if os.path.isdir(dir_path):
                anim_yaml = os.path.join(dir_path, "animation.yaml")
                if os.path.isfile(anim_yaml):
                    animations.append(name)

        return sorted(animations)

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

    # ======== Frame ========

    def get_frame(self, filename):
        if filename in self.frames:
            return self.frames[filename]
        return self._load_frame(filename)

    def set_frame(self, filename, frame_data):
        old_data = self.frames.get(filename)
        if old_data and frame_data.get_dict() == old_data.get_dict():
            return
        self.frames[filename] = frame_data
        self._save_frame(filename)

    def _load_frame(self, filename):
        frame = FrameData(joint_names=self.get_joint_names())
        path = self.resolve_frame_path(filename)
        if os.path.exists(path):
            frame.load_from_file(path)
        self.frames[filename] = frame
        return frame

    def _save_frame(self, filename):
        if filename in self.frames:
            path = self.resolve_frame_path(filename)
            self.frames[filename].save_to_file(path)

    # ======== Initial Frame ========
    def get_initial_frame(self):
        if self.initial_frame:
            return self.initial_frame
        return self._load_initial_frame()

    def set_initial_frame(self, frame_data):
        if self.initial_frame and frame_data.get_dict() == self.initial_frame.get_dict():
            return
        self.initial_frame = frame_data
        self._save_initial_frame()

    def _load_initial_frame(self):
        frame = FrameData(joint_names=self.get_joint_names())
        path = self.resolve_initial_frame_path()
        if os.path.exists(path):
            frame.load_from_file(path)
        self.initial_frame = frame
        return frame

    def _save_initial_frame(self):
        if self.initial_frame:
            path = self.resolve_initial_frame_path()
            self.initial_frame.save_to_file(path)

    # ======== If Condition ========
    def get_if(self, filename):
        if filename in self.ifs:
            return self.ifs[filename]
        return self._load_if(filename)

    def set_if(self, filename, if_data):
        old_data = self.ifs.get(filename)
        if old_data and if_data.get_dict() == old_data.get_dict():
            return
        self.ifs[filename] = if_data
        self._save_if(filename)

    def _load_if(self, filename):
        cond = IfConditionData()
        path = self.resolve_if_condition_path(filename)
        if os.path.exists(path):
            cond.load_from_file(path)
        self.ifs[filename] = cond
        return cond

    def _save_if(self, filename):
        if filename in self.ifs:
            path = self.resolve_if_condition_path(filename)
            self.ifs[filename].save_to_file(path)

    # ======== Switch Condition ========
    def get_switch(self, filename):
        if filename in self.switches:
            return self.switches[filename]
        return self._load_switch(filename)

    def set_switch(self, filename, switch_data):
        old_data = self.switches.get(filename)
        if old_data and switch_data.get_dict() == old_data.get_dict():
            return
        self.switches[filename] = switch_data
        self._save_switch(filename)

    def _load_switch(self, filename):
        cond = SwitchConditionData()
        path = self.resolve_switch_condition_path(filename)
        if os.path.exists(path):
            cond.load_from_file(path)
        self.switches[filename] = cond
        return cond

    def _save_switch(self, filename):
        if filename in self.switches:
            path = self.resolve_switch_condition_path(filename)
            self.switches[filename].save_to_file(path)

    # ======== Load All Items ========
    def load_all_items(self):
        """
        Load all items (initial frame, frames, if conditions, switch conditions)
        into memory to minimize file access during operation.
        """
        self._load_initial_frame()

        frame_files = self.list_frame_files()
        for frame_name in frame_files:
            self._load_frame(frame_name)

        if_files = self.list_if_condition_files()
        for if_name in if_files:
            self._load_if(if_name)

        switch_files = self.list_switch_condition_files()
        for switch_name in switch_files:
            self._load_switch(switch_name)

    # ======== Clear Cache ========
    def clear(self):
        """
        Clear all cached data. This should be called when switching animations
        to avoid stale data being used.
        """
        self.frames.clear()
        self.ifs.clear()
        self.switches.clear()
        self.initial_frame = None
