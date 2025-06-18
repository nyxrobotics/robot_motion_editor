import os
import shutil

import rospy

from .animation_file_manager import AnimationData
from .frame_file_manager import FrameData
from .if_condition_file_manager import IfConditionData
from .initial_pose_file_manager import InitialPoseData
from .switch_condition_file_manager import SwitchConditionData


class MotionFileManager:
    def __init__(self, motion_directory=None, joint_names=None):
        # Set Joint names
        self.joint_names = joint_names or []
        # Current Motion Data
        self.motion_directory = motion_directory
        self.motion_initial_pose = None
        # Current Animation Data
        self.animation_name = None
        self.animation_data = None
        self.animation_initial_frame = None
        self.animation_frames = {}
        self.animation_ifs = {}
        self.animation_switches = {}

    # === Public API ===

    # === Joint Names Management ===``
    def set_joint_names(self, joint_names):
        if self.joint_names == joint_names:
            return
        self.joint_names = joint_names

    def get_joint_names(self):
        return self.joint_names

    # === Motion Directory Management ===
    def set_motion_directory(self, directory):
        if self.motion_directory == directory:
            return
        if not os.path.isdir(directory):
            rospy.logerr(f"[MotionFileManager] Provided motion directory does not exist: {directory}")
            return
        self.motion_directory = directory
        self._clear_current_animation()
        self._load_initial_pose()

    def get_motion_directory(self):
        return self.motion_directory

    def set_initial_pose(self, initial_pose_data):
        if not isinstance(initial_pose_data, InitialPoseData):
            rospy.logwarn("[MotionFileManager] Invalid initial_pose_data provided.")
            return
        if self.motion_initial_pose and initial_pose_data.get_dict() == self.motion_initial_pose.get_dict():
            return
        self.motion_initial_pose = initial_pose_data
        self._save_initial_pose()

    def get_initial_pose(self):
        if self.motion_initial_pose:
            return self.motion_initial_pose
        return self._load_initial_pose()

    # === Animation Management ===
    def set_animation_name(self, name, skip_load=False):
        if self.animation_name == name:
            return
        if skip_load:
            self._clear_current_animation()
            self.animation_name = name
            return
        else:
            self._load_animation(name)

    def get_animation_name(self):
        if not self.animation_name:
            rospy.logwarn("[MotionFileManager] get_animation_name: No animation is currently loaded.")
        return self.animation_name

    def set_animation_data(self, animation_data):
        if not self.animation_name:
            rospy.logwarn("[MotionFileManager] No animation loaded to save.")
            return
        if not isinstance(animation_data, AnimationData):
            rospy.logwarn("[MotionFileManager] Invalid animation_data provided.")
            return
        if self.animation_data and animation_data.get_dict() == self.animation_data.get_dict():
            rospy.loginfo("[MotionFileManager] No changes detected in animation; skipping save.")
            return
        yaml_path = self._resolve_animation_yaml_path()
        if not yaml_path:
            return
        try:
            animation_data.save_to_file(yaml_path)
            self.animation_data = animation_data
            rospy.loginfo(f"[MotionFileManager] Saved animation: {self.animation_name}")
        except Exception as e:
            rospy.logerr(f"[MotionFileManager] Failed to save animation {self.animation_name}: {e}")

    def get_animation_data(self):
        if not self.animation_data:
            rospy.logwarn("[MotionFileManager] get_animation_data: No animation is currently loaded.")
        return self.animation_data

    def create_animation(self, animation_name):
        path = self._resolve_animation_path(animation_name)
        if os.path.exists(path):
            rospy.logwarn(f"[MotionFileManager] Animation already exists: {animation_name}")
            return
        try:
            os.makedirs(os.path.join(path, "frames"))
            os.makedirs(os.path.join(path, "conditions", "if"))
            os.makedirs(os.path.join(path, "conditions", "switch"))
            anim_data = AnimationData()
            anim_data.save_to_file(os.path.join(path, "animation.yaml"))
            rospy.loginfo(f"[MotionFileManager] Created new animation: {animation_name}")
        except Exception as e:
            rospy.logerr(f"[MotionFileManager] Failed to create animation {animation_name}: {e}")

    def rename_animation(self, old_name, new_name):
        old_path = self._resolve_animation_path(old_name)
        new_path = self._resolve_animation_path(new_name)
        if os.path.exists(new_path):
            rospy.logwarn(f"[MotionFileManager] Cannot rename: target animation {new_name} already exists.")
            return
        try:
            os.rename(old_path, new_path)
            rospy.loginfo(f"[MotionFileManager] Renamed animation: {old_name} -> {new_name}")
            if self.animation_name == old_name:
                self.animation_name = new_name
        except Exception as e:
            rospy.logerr(f"[MotionFileManager] Failed to rename animation {old_name} to {new_name}: {e}")

    def delete_animation(self, current_animation_name):
        path = self._resolve_animation_path(current_animation_name)
        if not os.path.exists(path):
            rospy.logwarn(f"[MotionFileManager] Animation does not exist: {current_animation_name}")
            return
        try:
            shutil.rmtree(path)
            rospy.loginfo(f"[MotionFileManager] Deleted animation: {current_animation_name}")
            if self.animation_name == current_animation_name:
                self._clear_current_animation()
        except Exception as e:
            rospy.logerr(f"[MotionFileManager] Failed to delete animation {current_animation_name}: {e}")

    # === Initial Frame ===
    def set_initial_frame(self, frame_data):
        if self.animation_initial_frame and frame_data.get_dict() == self.animation_initial_frame.get_dict():
            return
        self.animation_initial_frame = frame_data
        self._save_initial_frame()

    def get_initial_frame(self):
        if self.animation_initial_frame:
            return self.animation_initial_frame
        return self._load_initial_frame()

    # === Frame ===
    def set_frame(self, filename, frame_data):
        old_data = self.animation_frames.get(filename)
        if old_data and frame_data.get_dict() == old_data.get_dict():
            return
        self.animation_frames[filename] = frame_data
        self._save_frame(filename)

    def get_frame(self, filename):
        if filename in self.animation_frames:
            return self.animation_frames[filename]
        return self._load_frame(filename)

    def rename_frame(self, old_name, new_name):
        self._rename_file(self._resolve_frame_path(old_name), self._resolve_frame_path(new_name))
        self.animation_frames[new_name] = self.animation_frames.pop(old_name, None)

    def delete_frame(self, name):
        path = self._resolve_frame_path(name)
        if os.path.exists(path):
            os.remove(path)
            self.animation_frames.pop(name, None)

    # === If Condition ===
    def set_if(self, filename, if_data):
        old_data = self.animation_ifs.get(filename)
        if old_data and if_data.get_dict() == old_data.get_dict():
            return
        self.animation_ifs[filename] = if_data
        self._save_if(filename)

    def get_if(self, filename):
        if filename in self.animation_ifs:
            return self.animation_ifs[filename]
        return self._load_if(filename)

    def rename_if(self, old_name, new_name):
        self._rename_file(self._resolve_if_condition_path(old_name), self._resolve_if_condition_path(new_name))
        self.animation_ifs[new_name] = self.animation_ifs.pop(old_name, None)

    def delete_if(self, name):
        path = self._resolve_if_condition_path(name)
        if os.path.exists(path):
            os.remove(path)
            self.animation_ifs.pop(name, None)

    # === Switch Condition ===
    def set_switch(self, filename, switch_data):
        old_data = self.animation_switches.get(filename)
        if old_data and switch_data.get_dict() == old_data.get_dict():
            return
        self.animation_switches[filename] = switch_data
        self._save_switch(filename)

    def get_switch(self, filename):
        if filename in self.animation_switches:
            return self.animation_switches[filename]
        return self._load_switch(filename)

    def rename_switch(self, old_name, new_name):
        self._rename_file(self._resolve_switch_condition_path(old_name), self._resolve_switch_condition_path(new_name))
        self.animation_switches[new_name] = self.animation_switches.pop(old_name, None)

    def delete_switch(self, name):
        path = self._resolve_switch_condition_path(name)
        if os.path.exists(path):
            os.remove(path)
            self.animation_switches.pop(name, None)

    # === List Files ===
    def list_animation_directories(self):
        if not self.motion_directory or not os.path.isdir(self.motion_directory):
            rospy.logwarn("[MotionFileManager] Motion directory is not set or does not exist.")
            return []
        animation_dirs = []
        for name in os.listdir(self.motion_directory):
            dir_path = os.path.join(self.motion_directory, name)
            if os.path.isdir(dir_path):
                if os.path.isfile(os.path.join(dir_path, "animation.yaml")):
                    animation_dirs.append(name)
        return sorted(animation_dirs)

    def list_frame_files(self):
        if not self.motion_directory or not self.animation_name:
            return []
        path = os.path.join(self.motion_directory, self.animation_name, "frames")
        if not os.path.exists(path):
            return []
        return [f[:-5] for f in os.listdir(path) if f.endswith(".yaml")]

    def list_if_condition_files(self):
        if not self.motion_directory or not self.animation_name:
            return []
        path = os.path.join(self.motion_directory, self.animation_name, "conditions", "if")
        if not os.path.exists(path):
            return []
        return [f[:-5] for f in os.listdir(path) if f.endswith(".yaml")]

    def list_switch_condition_files(self):
        if not self.motion_directory or not self.animation_name:
            return []
        path = os.path.join(self.motion_directory, self.animation_name, "conditions", "switch")
        if not os.path.exists(path):
            return []
        return [f[:-5] for f in os.listdir(path) if f.endswith(".yaml")]

    # === Internal Utilities ===
    def _load_animation(self, name):
        if name is None or not name.strip():
            self._clear_current_animation()
            return
        self.animation_name = name
        yaml_path = self._resolve_animation_yaml_path()
        if not yaml_path or not os.path.exists(yaml_path):
            self.animation_name = None
            rospy.logwarn(f"[MotionFileManager] Animation file not found: {yaml_path}")
            return
        try:
            self._clear_current_animation()
            anim_data = AnimationData()
            anim_data.load_from_file(yaml_path)
            self.animation_name = name
            self.animation_data = anim_data
            self._load_animation_items()
            rospy.loginfo(f"[MotionFileManager] Loaded animation: {name}")
        except Exception as e:
            self.animation_name = None
            rospy.logerr(f"[MotionFileManager] Failed to load animation {name}: {e}")

    def _load_animation_items(self):
        self._load_initial_frame()
        for frame_name in self.list_frame_files():
            self._load_frame(frame_name)
        for if_name in self.list_if_condition_files():
            self._load_if(if_name)
        for switch_name in self.list_switch_condition_files():
            self._load_switch(switch_name)

    def _clear_current_animation(self):
        self.animation_name = None
        self.animation_data = None
        self.animation_frames.clear()
        self.animation_ifs.clear()
        self.animation_switches.clear()
        self.animation_initial_frame = None

    def _load_initial_pose(self):
        """
        Load the initial pose from the motion directory.

        Returns:
        - InitialPoseData: The loaded initial pose data.
        """
        if not self.motion_directory:
            rospy.logwarn("[MotionFileManager] Motion directory is not set.")
            return None
        path = os.path.join(self.motion_directory, "initial_pose.yaml")
        if not os.path.exists(path):
            rospy.logwarn(f"[MotionFileManager] Initial pose file does not exist: {path}")
            return None

        initial_pose_data = InitialPoseData()
        initial_pose_data.load_from_file(path)

        if not self.joint_names and initial_pose_data.get_joint_names():
            self.joint_names = initial_pose_data.get_joint_names()
        elif self.joint_names != initial_pose_data.get_joint_names():
            initial_pose_data.set_joint_names(self.joint_names)

        self.motion_initial_pose = initial_pose_data
        return initial_pose_data

    def _save_initial_pose(self):
        """
        Save the current initial pose to the motion directory.
        """
        if not self.motion_initial_pose:
            rospy.logwarn("[MotionFileManager] No initial pose set to save.")
            return
        if not self.motion_directory:
            rospy.logwarn("[MotionFileManager] Motion directory is not set.")
            return
        path = os.path.join(self.motion_directory, "initial_pose.yaml")
        try:
            self.motion_initial_pose.save_to_file(path)
            rospy.loginfo(f"[MotionFileManager] Saved initial pose to: {path}")
        except Exception as e:
            rospy.logerr(f"[MotionFileManager] Failed to save initial pose: {e}")

    def _load_initial_frame(self):
        frame = FrameData(joint_names=self.get_joint_names())
        path = self._resolve_initial_frame_path()
        if os.path.exists(path):
            frame.load_from_file(path)
        self.animation_initial_frame = frame
        return frame

    def _save_initial_frame(self):
        if self.animation_initial_frame:
            path = self.resolve_initial_frame_path()
            self.animation_initial_frame.save_to_file(path)

    def _load_frame(self, filename):
        frame = FrameData(joint_names=self.get_joint_names())
        path = self._resolve_frame_path(filename)
        if os.path.exists(path):
            frame.load_from_file(path)
        self.animation_frames[filename] = frame
        return frame

    def _save_frame(self, filename):
        if filename in self.animation_frames:
            path = self.resolve_frame_path(filename)
            self.animation_frames[filename].save_to_file(path)

    def _load_if(self, filename):
        cond = IfConditionData()
        path = self._resolve_if_condition_path(filename)
        if os.path.exists(path):
            cond.load_from_file(path)
        self.animation_ifs[filename] = cond
        return cond

    def _save_if(self, filename):
        if filename in self.animation_ifs:
            path = self.resolve_if_condition_path(filename)
            self.animation_ifs[filename].save_to_file(path)

    def _load_switch(self, filename):
        cond = SwitchConditionData()
        path = self._resolve_switch_condition_path(filename)
        if os.path.exists(path):
            cond.load_from_file(path)
        self.animation_switches[filename] = cond
        return cond

    def _save_switch(self, filename):
        if filename in self.animation_switches:
            path = self.resolve_switch_condition_path(filename)
            self.animation_switches[filename].save_to_file(path)

    def _rename_file(self, old_path, new_path):
        if os.path.exists(new_path):
            rospy.logwarn(f"[MotionFileManager] Cannot rename: target file {new_path} already exists.")
            return
        try:
            os.rename(old_path, new_path)
            rospy.loginfo(f"[MotionFileManager] Renamed file: {old_path} -> {new_path}")
        except Exception as e:
            rospy.logerr(f"[MotionFileManager] Failed to rename file {old_path} to {new_path}: {e}")

    def _rename_directory(self, old_path, new_path):
        try:
            os.rename(old_path, new_path)
            rospy.loginfo(f"[MotionFileManager] Renamed directory: {old_path} -> {new_path}")
            return True
        except Exception as e:
            rospy.logerr(f"[MotionFileManager] Failed to rename directory {old_path} to {new_path}: {e}")
            return False

    def _resolve_animation_path(self, name=None):
        anim_name = name or self.animation_name
        if not self.motion_directory or not anim_name:
            rospy.logerr("[MotionFileManager] motion_directory and animation name must be set before resolving paths.")
            return None
        return os.path.join(self.motion_directory, anim_name)

    def _resolve_animation_yaml_path(self):
        if not self.motion_directory or not self.animation_name:
            return None
        return os.path.join(self.motion_directory, self.animation_name, "animation.yaml")

    def _resolve_initial_pose_path(self):
        if not self.motion_directory:
            return None
        return os.path.join(self.motion_directory, "initial_pose.yaml")

    def _resolve_initial_frame_path(self):
        if not self.motion_directory or not self.animation_name:
            return None
        return os.path.join(self.motion_directory, self.animation_name, "initial_frame.yaml")

    def _resolve_frame_path(self, name):
        if not self.motion_directory or not self.animation_name:
            return None
        return os.path.join(self.motion_directory, self.animation_name, "frames", f"{name}.yaml")

    def _resolve_if_condition_path(self, name):
        if not self.motion_directory or not self.animation_name:
            return None
        return os.path.join(self.motion_directory, self.animation_name, "conditions", "if", f"{name}.yaml")

    def _resolve_switch_condition_path(self, name):
        if not self.motion_directory or not self.animation_name:
            return None
        return os.path.join(self.motion_directory, self.animation_name, "conditions", "switch", f"{name}.yaml")
