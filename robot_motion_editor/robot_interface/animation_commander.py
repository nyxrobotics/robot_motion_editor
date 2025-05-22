import threading
import time

import rospy

from ..gui.animation_editor_widget import FrameBlockItem
from ..gui.animation_editor_widget import IfBlockItem
from ..gui.animation_editor_widget import StartBlockItem
from ..gui.animation_editor_widget import SwitchBlockItem


class AnimationCommander:
    def __init__(self, scene, frame_loader, trajectory_commander, initial_joint_state=None):
        """
        Args:
            scene: Animation scene with block graph
            frame_loader: Function to load a frame by name, returns (JointState, move_duration, wait_duration)
            trajectory_commander: Instance of TrajectoryCommander
            initial_joint_state: Optional initial JointState to start from
        """
        self.scene = scene
        self.load_frame = frame_loader
        self.trajectory_commander = trajectory_commander
        self.initial_joint_state = initial_joint_state

        self._thread = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._lock = threading.Lock()

        self.state = 'stopped'
        self.current_block = None
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

    def _get_start_block(self):
        for block in self.scene.block_objects.values():
            if isinstance(block, StartBlockItem):
                return self._get_next_block(block)
        return None

    def _get_next_block(self, block):
        if isinstance(block, FrameBlockItem):
            return block.output_arrows[0].end_item if block.output_arrows else None
        elif isinstance(block, (IfBlockItem, SwitchBlockItem)):
            idx = block.preview_output_index
            outputs = list(block.output_sub_blocks.values())
            if 0 <= idx < len(outputs):
                sub = outputs[idx]
                if sub.output_arrows:
                    return sub.output_arrows[0].end_item
        elif isinstance(block, StartBlockItem):
            return block.output_arrows[0].end_item if block.output_arrows else None
        return None

    def _run(self, start_block=None):
        self.current_block = start_block or self._get_start_block()
        previous_joint_state = self.initial_joint_state

        while self.current_block and not self._stop_event.is_set():
            self._pause_event.wait()

            if not isinstance(self.current_block, FrameBlockItem):
                self.current_block = self._get_next_block(self.current_block)
                continue

            frame_name = self.current_block.filename
            try:
                target_joint_state, move_duration, wait_duration = self.load_frame(frame_name)
            except Exception as e:
                rospy.logwarn(f"[AnimationCommander] Failed to load frame '{frame_name}': {e}")
                self.stop()
                return

            if previous_joint_state is None:
                previous_joint_state = target_joint_state

            self.trajectory_commander.send_joint_state(target_joint_state, duration=move_duration)

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
            self.current_block = self._get_next_block(self.current_block)

        self.state = 'stopped'
