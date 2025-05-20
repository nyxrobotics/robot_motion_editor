import threading
import time

from ..gui.motion_editor_scene import FrameBlockItem
from ..gui.motion_editor_scene import IfBlockItem
from ..gui.motion_editor_scene import StartBlockItem
from ..gui.motion_editor_scene import SwitchBlockItem


class AnimationPreviewVisualizer:
    def __init__(self, scene, trajectory_visualizer, frame_loader, initial_joint_state=None):
        self.scene = scene
        self.visualizer = trajectory_visualizer
        self.load_frame = frame_loader
        self.initial_joint_state = initial_joint_state

        self._thread = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._lock = threading.Lock()

        self.state = 'stopped'
        self.current_block = None
        self.next_block = None
        self._prev_snapshot = self._get_scene_snapshot()

        self._pause_event.set()  # 初期状態は再生可能

    def start(self):
        self.visualizer.enable_loop(False)
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._pause_event.set()
            self.state = 'playing'
            self._prev_snapshot = self._get_scene_snapshot()
            self._thread = threading.Thread(target=self._run)
            self._thread.start()

    def pause(self):
        with self._lock:
            self.state = 'paused'
            self._pause_event.clear()  # 停止中にする

    def resume(self):
        with self._lock:
            self.state = 'playing'
            self._pause_event.set()  # 再生状態にする

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
        for name, block in self.scene.block_objects.items():
            entry = {
                'id': getattr(block, 'id', None),
                'type': type(block).__name__,
                'filename': getattr(block, 'filename', ''),
                'preview_output_index': getattr(block, 'preview_output_index', None),
                'num_outputs': len(getattr(block, 'output_arrows', [])),
                'subblock_keys': sorted(block.output_sub_blocks.keys())
                if hasattr(block, 'output_sub_blocks') else [],
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

    def _run(self):
        self.current_block = self._get_start_block()
        previous_joint_state = self.initial_joint_state

        while self.current_block and not self._stop_event.is_set():
            self._pause_event.wait()

            if self._scene_changed():
                print("[AnimationPreviewVisualizer] Scene changed. Stopping.")
                self.stop()
                return

            if not isinstance(self.current_block, FrameBlockItem):
                self.current_block = self._get_next_block(self.current_block)
                continue

            frame_name = self.current_block.filename
            try:
                target_joint_state, move_duration, wait_duration = self.load_frame(frame_name)
            except Exception as e:
                print(f"[Visualizer] Failed to load frame {frame_name}: {e}")
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
                self._pause_event.wait()
                time.sleep(0.001)
                elapsed = time.perf_counter() - start_time

            previous_joint_state = target_joint_state
            self.current_block = self._get_next_block(self.current_block)
