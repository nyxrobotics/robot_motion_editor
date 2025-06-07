import os
import threading
import time

import rospy
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint

from ..gui.animation_editor_items import StartBlockItem
from ..gui.animation_editor_widget import FrameBlockItem
from ..logic.frame_file_manager import FrameData
from ..logic.initial_pose_file_manager import InitialPoseData
from ..logic.joint_data_manager import JointDataManager
from ..logic.motion_directory_manager import MotionDirectoryManager
from .trajectory_commander import TrajectoryCommander


def joint_states_equal(js1, js2, tol=1e-4):
    if js1 is None or js2 is None:
        return False
    if js1.name != js2.name:
        return False
    return all(abs(a - b) < tol for a, b in zip(js1.position, js2.position))


class AnimationCommander:
    def __init__(self, animation_flow_scene, trajectory_commander: TrajectoryCommander,
                 motion_directory_manager: MotionDirectoryManager,
                 joint_data_manager: JointDataManager):
        self.animation_flow_scene = animation_flow_scene
        self.trajectory_commander = trajectory_commander
        self.motion_directory_manager = motion_directory_manager
        self.joint_data_manager = joint_data_manager

        self.initial_joint_state = None
        try:
            pose_path = self.motion_directory_manager.resolve_initial_pose_path()
            if os.path.exists(pose_path):
                pose_data = InitialPoseData()
                pose_data.set_joint_names(self.joint_data_manager.get_joint_names())
                pose_data.load_from_file(pose_path)
                self.initial_joint_state = pose_data.get_joint_state()
        except Exception as e:
            rospy.logwarn(f"[AnimationCommander] Failed to load initial pose: {e}")

        self._thread = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._lock = threading.Lock()

        self.state = 'stopped'
        self.current_block = None
        self.previous_target_joint_state = self.initial_joint_state
        self._pause_event.set()

    def start(self, start_block=None):
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._pause_event.set()
            self.state = 'playing'
            self._thread = threading.Thread(target=self._run, args=(start_block,))
            self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._pause_event.set()
        self.state = 'stopped'
        if self._thread:
            self._thread.join()

    def pause(self):
        with self._lock:
            self.state = 'paused'
            self._pause_event.clear()

    def resume(self):
        with self._lock:
            self.state = 'playing'
            self._pause_event.set()

    def _run(self, start_block=None):
        self.current_block = start_block or self.animation_flow_scene.get_start_block()

        if self.previous_target_joint_state and self.initial_joint_state and \
           not joint_states_equal(self.previous_target_joint_state, self.initial_joint_state):
            self.trajectory_commander.send_movement(
                self.previous_target_joint_state, self.initial_joint_state, duration=1.0)
            self.previous_target_joint_state = self.initial_joint_state
            time.sleep(1.0)

        while self.current_block and not self._stop_event.is_set() and not rospy.is_shutdown():
            self._pause_event.wait()

            if not isinstance(self.current_block, FrameBlockItem):
                self.current_block = self.animation_flow_scene.get_next_frame_block(self.current_block)
                continue

            frame_name = self.current_block.filename
            try:
                frame_path = self.motion_directory_manager.resolve_frame_path(frame_name)
                frame_data = FrameData()
                frame_data.set_joint_names(self.joint_data_manager.get_joint_names())
                frame_data.load_from_file(frame_path)
                target_joint_state = frame_data.get_joint_state()
                move_duration = frame_data.move_duration
                wait_duration = frame_data.wait_duration
            except Exception as e:
                rospy.logwarn(f"[AnimationCommander] Failed to load frame '{frame_name}': {e}")
                self.stop()
                return

            if self.previous_target_joint_state is None:
                self.previous_target_joint_state = target_joint_state

            self.trajectory_commander.send_movement(
                self.previous_target_joint_state, target_joint_state, move_duration)

            total_duration = move_duration + wait_duration
            elapsed = 0.0
            start_time = time.perf_counter()

            while elapsed < total_duration:
                if self._stop_event.is_set() or rospy.is_shutdown():
                    return
                if self.state == 'paused':
                    self._pause_event.wait()
                    start_time = time.perf_counter() - elapsed
                time.sleep(0.001)
                elapsed = time.perf_counter() - start_time

            self.previous_target_joint_state = target_joint_state
            self.current_block = self.animation_flow_scene.get_next_frame_block(self.current_block)

        self.state = 'stopped'

    def play_single_block(self, block):
        if isinstance(block, FrameBlockItem):
            frame_name = block.filename
            try:
                frame_path = self.motion_directory_manager.resolve_frame_path(frame_name)
                frame_data = FrameData()
                frame_data.set_joint_names(self.joint_data_manager.get_joint_names())
                frame_data.load_from_file(frame_path)
                target_joint_state = frame_data.get_joint_state()
                move_duration = frame_data.move_duration
            except Exception as e:
                rospy.logwarn(f"[AnimationCommander] Failed to load frame '{frame_name}': {e}")
                return

            current_joint_state = self.previous_target_joint_state or self.initial_joint_state
            if current_joint_state is None:
                rospy.logwarn("[AnimationCommander] Cannot determine current joint state.")
                return

            self.trajectory_commander.send_movement(current_joint_state, target_joint_state, move_duration)
            self.previous_target_joint_state = target_joint_state
            rospy.loginfo(f"[Commander] Played single frame: {frame_name}")

        elif isinstance(block, StartBlockItem):
            try:
                frame_path = self.motion_directory_manager.resolve_initial_frame_path()
                frame_data = FrameData()
                frame_data.set_joint_names(self.joint_data_manager.get_joint_names())
                frame_data.load_from_file(frame_path)
                target_joint_state = frame_data.get_joint_state()
            except Exception as e:
                rospy.logwarn(f"[AnimationCommander] Failed to load initial frame: {e}")

            current_joint_state = self.previous_target_joint_state or self.initial_joint_state
            if current_joint_state is None:
                rospy.logwarn("[AnimationCommander] No initial_joint_state set for StartBlockItem execution.")
                return

            self.trajectory_commander.send_movement(current_joint_state, target_joint_state, move_duration)
            self.previous_target_joint_state = current_joint_state
            rospy.loginfo("[Commander] Played StartBlockItem with initial_joint_state.")
