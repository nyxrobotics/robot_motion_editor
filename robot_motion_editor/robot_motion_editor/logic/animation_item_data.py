import os

from .frame_file_manager import FrameData
from .if_condition_file_manager import IfConditionData

from .switch_condition_file_manager import SwitchConditionData


class AnimationItemData:
    def __init__(self, motion_directory_manager):
        self.motion_directory_manager = motion_directory_manager
        self.frames = {}
        self.ifs = {}
        self.switches = {}
        self.initial_frame = None

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
        frame = FrameData(joint_names=self.motion_directory_manager.get_joint_names())
        path = self.motion_directory_manager.resolve_frame_path(filename)
        if os.path.exists(path):
            frame.load_from_file(path)
        self.frames[filename] = frame
        return frame

    def _save_frame(self, filename):
        if filename in self.frames:
            path = self.motion_directory_manager.resolve_frame_path(filename)
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
        frame = FrameData(joint_names=self.motion_directory_manager.get_joint_names())
        path = self.motion_directory_manager.resolve_initial_frame_path()
        if os.path.exists(path):
            frame.load_from_file(path)
        self.initial_frame = frame
        return frame

    def _save_initial_frame(self):
        if self.initial_frame:
            path = self.motion_directory_manager.resolve_initial_frame_path()
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
        path = self.motion_directory_manager.resolve_if_condition_path(filename)
        if os.path.exists(path):
            cond.load_from_file(path)
        self.ifs[filename] = cond
        return cond

    def _save_if(self, filename):
        if filename in self.ifs:
            path = self.motion_directory_manager.resolve_if_condition_path(filename)
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
        path = self.motion_directory_manager.resolve_switch_condition_path(filename)
        if os.path.exists(path):
            cond.load_from_file(path)
        self.switches[filename] = cond
        return cond

    def _save_switch(self, filename):
        if filename in self.switches:
            path = self.motion_directory_manager.resolve_switch_condition_path(filename)
            self.switches[filename].save_to_file(path)

    # ======== Load All Items ========
    def load_all_items(self):
        """
        Load all items (initial frame, frames, if conditions, switch conditions)
        into memory to minimize file access during operation.
        """
        self._load_initial_frame()

        frame_files = self.motion_directory_manager.list_frame_files()
        for frame_name in frame_files:
            self._load_frame(frame_name)

        if_files = self.motion_directory_manager.list_if_condition_files()
        for if_name in if_files:
            self._load_if(if_name)

        switch_files = self.motion_directory_manager.list_switch_condition_files()
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
