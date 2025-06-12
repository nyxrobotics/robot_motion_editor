import os
import threading
import time

import rospy
from sensor_msgs.msg import JointState

from ..gui.animation_editor_items import FrameBlockItem
from ..gui.animation_editor_items import StartBlockItem
from ..logic.frame_file_manager import FrameData
from ..logic.initial_pose_file_manager import InitialPoseData
from ..logic.joint_data_manager import JointDataManager
from ..logic.motion_directory_manager import MotionDirectoryManager
from .trajectory_visualizer import TrajectoryVisualizer


def joint_states_equal(js1, js2, tol=1e-4):
    if js1 is None or js2 is None:
        return False
    if js1.name != js2.name:
        return False
    return all(abs(a - b) < tol for a, b in zip(js1.position, js2.position))


class AnimationVisualizer:
    def __init__(self, animation_flow_scene,
                 trajectory_visualizer: TrajectoryVisualizer,
                 motion_directory_manager: MotionDirectoryManager,
                 joint_data_manager: JointDataManager):
        self.animation_flow_scene = animation_flow_scene
        self.visualizer = trajectory_visualizer
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
            rospy.logwarn(f"[AnimationVisualizer] Failed to load initial pose: {e}")

        self._current_target_state = self.initial_joint_state
        self._prev_snapshot = self._get_scene_snapshot()

        self._thread = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._lock = threading.Lock()

        self.state = 'stopped'
        self.current_block = None

        self._pause_event.set()

    def start(self, start_block=None):
        self.visualizer.enable_loop(False)
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._pause_event.set()
            self.state = 'playing'
            self._prev_snapshot = self._get_scene_snapshot()

            if self._current_target_state is None:
                if self.initial_joint_state is not None:
                    rospy.loginfo("[AnimationVisualizer] Setting current state to initial pose.")
                    self._current_target_state = self.initial_joint_state
                else:
                    rospy.logwarn("[AnimationVisualizer] No initial pose found. Will use first frame as starting point.")

            self._thread = threading.Thread(target=self._run, args=(start_block,))
            self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._pause_event.set()
        self.state = 'stopped'
        if self._thread:
            self._thread.join()
        if isinstance(self.current_block, (FrameBlockItem, StartBlockItem)):
            try:
                joint_state, _, _ = self.extract_joint_state_and_duration(self.current_block)
                self._current_target_state = joint_state
            except Exception as e:
                rospy.logwarn(f"[AnimationVisualizer] Failed to extract joint state: {e}")

    def pause(self):
        with self._lock:
            self.state = 'paused'
            self._pause_event.clear()

    def resume(self):
        with self._lock:
            self.state = 'playing'
            self._pause_event.set()

    def _get_scene_snapshot(self):
        snapshot = {}
        for name, block in self.animation_flow_scene.block_objects.items():
            snapshot[name] = {
                'id': getattr(block, 'id', None),
                'type': type(block).__name__,
                'filename': getattr(block, 'filename', ''),
                'preview_output_index': getattr(block, 'preview_output_index', None),
                'num_outputs': len(getattr(block, 'output_arrows', [])),
                'subblock_keys': sorted(block.output_sub_blocks.keys()) if hasattr(block, 'output_sub_blocks') else [],
            }
        return snapshot

    def _scene_changed(self):
        current = self._get_scene_snapshot()
        if current.keys() != self._prev_snapshot.keys():
            return True
        for name in current:
            prev = self._prev_snapshot[name]
            curr = current[name]
            for key in curr:
                if key == 'preview_output_index':
                    continue
                if curr[key] != prev.get(key):
                    return True
        return False

    def _run(self, start_block=None):
        self.current_block = start_block or self.animation_flow_scene.get_start_block()
        start_target, move_duration, wait_duration = self.extract_joint_state_and_duration(self.current_block)

        if self._current_target_state and start_target and \
                not joint_states_equal(self._current_target_state, start_target):
            self.visualizer.send_movement(
                self._current_target_state, start_target, duration=1.0)
            self.visualizer.visualize_goal_state(start_target)
            self._current_target_state = start_target
            time.sleep(1.0)

        while self.current_block and not self._stop_event.is_set() and not rospy.is_shutdown():
            self._pause_event.wait()

            if self._scene_changed():
                rospy.logwarn("[AnimationVisualizer] Scene changed. Stopping.")
                self.stop()
                return

            if self.animation_flow_scene is not None:
                selected = self.animation_flow_scene.selectedItems()
                if self.current_block not in selected:
                    for item in selected:
                        item.setSelected(False)
                    if hasattr(self.current_block, 'setSelected'):
                        self.current_block.setSelected(True)
                        self.current_block.update()

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
                rospy.logwarn(f"[AnimationVisualizer] Failed to load frame '{frame_name}': {e}")
                self.stop()
                return

            if self._current_target_state is None:
                rospy.logwarn("[AnimationVisualizer] No previous_target_joint_state set for playback.")
                self._current_target_state = target_joint_state

            self.visualizer.send_movement(
                self._current_target_state, target_joint_state, move_duration)
            self.visualizer.visualize_goal_state(target_joint_state)

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

            self._current_target_state = target_joint_state
            self.current_block = self.animation_flow_scene.get_next_frame_block(self.current_block)

            if self.animation_flow_scene is not None:
                for item in self.animation_flow_scene.selectedItems():
                    item.setSelected(False)

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
                rospy.logwarn(f"[AnimationVisualizer] Failed to load frame '{frame_name}': {e}")
                return

            if self._current_target_state is None:
                rospy.logwarn("[AnimationVisualizer] No previous_target_joint_state set for single frame playback.")
                self._current_target_state = target_joint_state
                return

            self.visualizer.send_movement(self._current_target_state, target_joint_state, move_duration)
            self.visualizer.visualize_goal_state(target_joint_state)
            self._current_target_state = target_joint_state
            rospy.loginfo(f"[Visualizer] Played single frame: {frame_name}")

        elif isinstance(block, StartBlockItem):
            try:
                frame_path = self.motion_directory_manager.resolve_initial_frame_path()
                frame_data = FrameData()
                frame_data.set_joint_names(self.joint_data_manager.get_joint_names())
                frame_data.load_from_file(frame_path)
                target_joint_state = frame_data.get_joint_state()
            except Exception as e:
                rospy.logwarn(f"[AnimationVisualizer] Failed to load initial frame: {e}")

            if self._current_target_state is None:
                rospy.logwarn("[AnimationVisualizer] No previous_target_joint_state set for StartBlockItem playback.")
                self._current_target_state = target_joint_state
                return

            self.visualizer.send_movement(self._current_target_state, target_joint_state, move_duration)
            self.visualizer.visualize_goal_state(target_joint_state)
            self._current_target_state = target_joint_state
            rospy.loginfo("[Visualizer] Played StartBlockItem.")

    def extract_joint_state_and_duration(self, block):

        if isinstance(block, FrameBlockItem):
            path = self.motion_directory_manager.resolve_frame_path(block.filename)
        elif isinstance(block, StartBlockItem):
            path = self.motion_directory_manager.resolve_initial_frame_path()
        else:
            return None, 0.0, 0.0

        frame_data = FrameData()
        frame_data.set_joint_names(self.joint_data_manager.get_joint_names())
        frame_data.load_from_file(path)

        return frame_data.get_joint_state(), frame_data.move_duration, frame_data.wait_duration
