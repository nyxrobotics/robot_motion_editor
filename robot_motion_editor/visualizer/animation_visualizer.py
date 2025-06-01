import os
import threading
import time

import rospy

from ..gui.animation_editor_items import FrameBlockItem
from ..gui.animation_editor_items import IfBlockItem
from ..gui.animation_editor_items import StartBlockItem
from ..gui.animation_editor_items import SwitchBlockItem
from ..logic.frame_file_manager import FrameData
from ..logic.initial_pose_file_manager import InitialPoseData
from ..logic.joint_data_manager import JointDataManager
from ..logic.motion_directory_manager import MotionDirectoryManager


class AnimationVisualizer:
    def __init__(
            self,
            animation_flow_scene,
            trajectory_visualizer,
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
            rospy.logwarn(f"Failed to load initial pose: {e}")

        self._thread = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._lock = threading.Lock()

        self.state = 'stopped'
        self.current_block = None
        self.next_block = None
        self._prev_snapshot = self._get_scene_snapshot()

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
            self._thread = threading.Thread(target=self._run, args=(start_block,))
            self._thread.start()

    def pause(self):
        with self._lock:
            self.state = 'paused'
            self._pause_event.clear()

    def resume(self):
        with self._lock:
            self.state = 'playing'
            self._pause_event.set()

    def stop(self):
        self._stop_event.set()
        self._pause_event.set()
        self.state = 'stopped'
        if self._thread:
            self._thread.join()

    def update_scene(self, new_scene):
        with self._lock:
            self.scene = new_scene

    def _get_scene_snapshot(self):
        snapshot = {}
        for name, block in self.animation_flow_scene.block_objects.items():
            entry = {
                'id': getattr(block, 'id', None),
                'type': type(block).__name__,
                'filename': getattr(block, 'filename', ''),
                'preview_output_index': getattr(block, 'preview_output_index', None),
                'num_outputs': len(getattr(block, 'output_arrows', [])),
                'subblock_keys': sorted(block.output_sub_blocks.keys()) if hasattr(block, 'output_sub_blocks') else [],
            }
            snapshot[name] = entry
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
        self.current_block = start_block or self.animation_flow_scene.get_first_frame_block()
        previous_joint_state = self.initial_joint_state

        while self.current_block and not self._stop_event.is_set():
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

            if previous_joint_state is None:
                previous_joint_state = target_joint_state

            self.visualizer.visualize_current2target(previous_joint_state, target_joint_state, move_duration)
            self.visualizer.publish_goal_state(target_joint_state)

            total_duration = move_duration + wait_duration
            elapsed = 0.0
            start_time = time.perf_counter()

            while elapsed < total_duration:
                if self._stop_event.is_set():
                    return
                if self.state == 'paused':
                    self._pause_event.wait()
                    start_time = time.perf_counter() - elapsed
                time.sleep(0.001)
                elapsed = time.perf_counter() - start_time

            previous_joint_state = target_joint_state
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
                wait_duration = frame_data.wait_duration
            except Exception as e:
                rospy.logwarn(f"[AnimationVisualizer] Failed to load frame '{frame_name}': {e}")
                return

            current_joint_state = self.initial_joint_state
            if current_joint_state is None:
                return

            self.visualizer.visualize_current2target(
                current=current_joint_state,
                target=target_joint_state,
                duration=move_duration
            )
            self.visualizer.publish_goal_state(target_joint_state)
            self.previous_joint_state = target_joint_state
            rospy.loginfo(f"[Visualizer] Played single frame: {frame_name}")

        elif isinstance(block, StartBlockItem):
            current_joint_state = self.initial_joint_state
            try:
                frame_path = self.motion_directory_manager.resolve_initial_frame_path()
                frame_data = FrameData()
                frame_data.set_joint_names(self.joint_data_manager.get_joint_names())
                frame_data.load_from_file(frame_path)
                current_joint_state = frame_data.get_joint_state()
            except Exception as e:
                rospy.logwarn(f"[AnimationVisualizer] Failed to load initial frame: {e}")

            if current_joint_state is None:
                rospy.logwarn("[AnimationVisualizer] No initial_joint_state set for StartBlockItem visualization.")
                return

            self.visualizer.publish_goal_state(current_joint_state)
            rospy.loginfo("[Visualizer] Played StartBlockItem with initial_joint_state.")
