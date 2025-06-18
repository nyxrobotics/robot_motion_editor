import os
import shutil

import rospy

from .frame_file_manager import FrameData
from .if_condition_file_manager import IfConditionData
from .switch_condition_file_manager import SwitchConditionData


class MotionFileManager:
    def __init__(self, motion_directory=None, joint_names=None):
        self.motion_directory = motion_directory
        self.current_animation_name = None
        self.joint_names = joint_names or []
        self.frames = {}
        self.ifs = {}
        self.switches = {}
        self.initial_frame = None

    # === Public API ===
    def set_joint_names(self, joint_names):
        if self.joint_names == joint_names:
            return
        self.joint_names = joint_names

    def get_joint_names(self):
        return self.joint_names

    def set_motion_directory(self, directory):
        if self.motion_directory == directory:
            return
        if not os.path.isdir(directory):
            rospy.logerr(f"Provided motion directory does not exist: {directory}")
            return
        self.motion_directory = directory
        self.current_animation_name = None
        self._clear_animation_items()

    def get_motion_directory(self):
        return self.motion_directory

    def set_current_animation(self, animation_name):
        if self.current_animation_name == animation_name:
            return
        self.current_animation_name = animation_name
        self._clear_animation_items()
        self._load_animation_items()

    def get_current_animation(self):
        return self.current_animation_name

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

    def rename_frame(self, old_name, new_name):
        self._rename_file(self._resolve_frame_path(old_name), self._resolve_frame_path(new_name))
        self.frames[new_name] = self.frames.pop(old_name, None)

    def delete_frame(self, name):
        path = self._resolve_frame_path(name)
        if os.path.exists(path):
            os.remove(path)
            self.frames.pop(name, None)

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

    def rename_if(self, old_name, new_name):
        self._rename_file(self._resolve_if_condition_path(old_name), self._resolve_if_condition_path(new_name))
        self.ifs[new_name] = self.ifs.pop(old_name, None)

    def delete_if(self, name):
        path = self._resolve_if_condition_path(name)
        if os.path.exists(path):
            os.remove(path)
            self.ifs.pop(name, None)

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

    def rename_switch(self, old_name, new_name):
        self._rename_file(self._resolve_switch_condition_path(old_name), self._resolve_switch_condition_path(new_name))
        self.switches[new_name] = self.switches.pop(old_name, None)

    def delete_switch(self, name):
        path = self._resolve_switch_condition_path(name)
        if os.path.exists(path):
            os.remove(path)
            self.switches.pop(name, None)

    # ======== Animation Management ========
    def create_animation(self, animation_name):
        """
        Create a new animation directory with default structure.
        """
        if not self.motion_directory:
            rospy.logerr("Motion directory is not set.")
            return False

        anim_path = self._resolve_animation_path(animation_name)
        if os.path.exists(anim_path):
            rospy.logwarn(f"Animation '{animation_name}' already exists at {anim_path}.")
            return False

        try:
            os.makedirs(os.path.join(anim_path, "frames"))
            os.makedirs(os.path.join(anim_path, "conditions", "if"))
            os.makedirs(os.path.join(anim_path, "conditions", "switch"))

            # Create empty animation.yaml
            anim_yaml_path = os.path.join(anim_path, "animation.yaml")
            with open(anim_yaml_path, "w") as f:
                f.write("# New animation\n")

            rospy.loginfo(f"Created new animation directory at {anim_path}.")
            return True
        except Exception as e:
            rospy.logerr(f"Failed to create animation '{animation_name}': {e}")
            return False

    def rename_animation(self, old_name, new_name):
        old_path = self._resolve_animation_path(old_name)
        new_path = self._resolve_animation_path(new_name)
        if not os.path.exists(old_path):
            rospy.logwarn(f"Cannot rename: animation '{old_name}' does not exist at {old_path}")
            return False
        if os.path.exists(new_path):
            rospy.logwarn(f"Cannot rename: target animation '{new_name}' already exists at {new_path}")
            return False
        success = self._rename_directory(old_path, new_path)
        if success and self.current_animation_name == old_name:
            self.current_animation_name = new_name
        return success

    def delete_animation(self, animation_name):
        """
        Delete an animation directory.
        """
        if not self.motion_directory:
            rospy.logerr("Motion directory is not set.")
            return False

        anim_path = self._resolve_animation_path(animation_name)
        if not os.path.exists(anim_path):
            rospy.logwarn(f"Animation '{animation_name}' does not exist at {anim_path}.")
            return False

        if self.current_animation_name == animation_name:
            self.current_animation_name = None
            self._clear_animation_items()

        try:
            shutil.rmtree(anim_path)
            rospy.loginfo(f"Deleted animation directory at {anim_path}.")
            if self.current_animation_name == animation_name:
                self.current_animation_name = None
                self._clear_animation_items()
            return True
        except Exception as e:
            rospy.logerr(f"Failed to delete animation '{animation_name}': {e}")
            return False

    def list_animation_directories(self):
        if not self.motion_directory or not os.path.isdir(self.motion_directory):
            rospy.logwarn("Motion directory is not set or does not exist.")
            return []
        animation_dirs = []
        for name in os.listdir(self.motion_directory):
            dir_path = os.path.join(self.motion_directory, name)
            if os.path.isdir(dir_path):
                if os.path.isfile(os.path.join(dir_path, "animation.yaml")):
                    animation_dirs.append(name)
        return sorted(animation_dirs)

    def list_frame_files(self):
        path = os.path.join(self.motion_directory, self.current_animation_name, "frames")
        if not os.path.exists(path):
            return []
        return [f[:-5] for f in os.listdir(path) if f.endswith(".yaml")]

    def list_if_condition_files(self):
        path = os.path.join(self.motion_directory, self.current_animation_name, "conditions", "if")
        if not os.path.exists(path):
            return []
        return [f[:-5] for f in os.listdir(path) if f.endswith(".yaml")]

    def list_switch_condition_files(self):
        path = os.path.join(self.motion_directory, self.current_animation_name, "conditions", "switch")
        if not os.path.exists(path):
            return []
        return [f[:-5] for f in os.listdir(path) if f.endswith(".yaml")]

    # === Internal Utilities ===
    def _load_animation_items(self):
        self._load_initial_frame()
        for frame_name in self.list_frame_files():
            self._load_frame(frame_name)
        for if_name in self.list_if_condition_files():
            self._load_if(if_name)
        for switch_name in self.list_switch_condition_files():
            self._load_switch(switch_name)

    def _clear_animation_items(self):
        self.frames.clear()
        self.ifs.clear()
        self.switches.clear()
        self.initial_frame = None

    def _rename_file(self, old_path, new_path):
        if os.path.exists(new_path):
            rospy.logwarn(f"Cannot rename: target file {new_path} already exists.")
            return
        try:
            os.rename(old_path, new_path)
            rospy.loginfo(f"Renamed file: {old_path} -> {new_path}")
        except Exception as e:
            rospy.logerr(f"Failed to rename file {old_path} to {new_path}: {e}")

    def _rename_directory(self, old_path, new_path):
        try:
            os.rename(old_path, new_path)
            rospy.loginfo(f"Renamed directory: {old_path} -> {new_path}")
            return True
        except Exception as e:
            rospy.logerr(f"Failed to rename directory {old_path} to {new_path}: {e}")
            return False

    def _resolve_animation_path(self, name=None):
        anim_name = name or self.current_animation_name
        if not self.motion_directory or not anim_name:
            rospy.logerr("motion_directory and animation name must be set before resolving paths.")
            return None
        return os.path.join(self.motion_directory, anim_name)

    def _resolve_initial_frame_path(self):
        return os.path.join(self.motion_directory, self.current_animation_name, "initial_frame.yaml")

    def _resolve_frame_path(self, name):
        return os.path.join(self.motion_directory, self.current_animation_name, "frames", f"{name}.yaml")

    def _resolve_if_condition_path(self, name):
        return os.path.join(self.motion_directory, self.current_animation_name, "conditions", "if", f"{name}.yaml")

    def _resolve_switch_condition_path(self, name):
        return os.path.join(self.motion_directory, self.current_animation_name, "conditions", "switch", f"{name}.yaml")

    def _resolve_animation_yaml_path(self):
        return os.path.join(self.motion_directory, self.current_animation_name, "animation.yaml")

    def _resolve_initial_pose_path(self):
        return os.path.join(self.motion_directory, "initial_pose.yaml")

    def _load_frame(self, filename):
        frame = FrameData(joint_names=self.get_joint_names())
        path = self._resolve_frame_path(filename)
        if os.path.exists(path):
            frame.load_from_file(path)
        self.frames[filename] = frame
        return frame

    def _load_initial_frame(self):
        frame = FrameData(joint_names=self.get_joint_names())
        path = self._resolve_initial_frame_path()
        if os.path.exists(path):
            frame.load_from_file(path)
        self.initial_frame = frame
        return frame

    def _load_if(self, filename):
        cond = IfConditionData()
        path = self._resolve_if_condition_path(filename)
        if os.path.exists(path):
            cond.load_from_file(path)
        self.ifs[filename] = cond
        return cond

    def _load_switch(self, filename):
        cond = SwitchConditionData()
        path = self._resolve_switch_condition_path(filename)
        if os.path.exists(path):
            cond.load_from_file(path)
        self.switches[filename] = cond
        return cond

    def _save_frame(self, filename):
        if filename in self.frames:
            path = self.resolve_frame_path(filename)
            self.frames[filename].save_to_file(path)

    def _save_initial_frame(self):
        if self.initial_frame:
            path = self.resolve_initial_frame_path()
            self.initial_frame.save_to_file(path)

    def _save_if(self, filename):
        if filename in self.ifs:
            path = self.resolve_if_condition_path(filename)
            self.ifs[filename].save_to_file(path)

    def _save_switch(self, filename):
        if filename in self.switches:
            path = self.resolve_switch_condition_path(filename)
            self.switches[filename].save_to_file(path)
