import threading
import time

from ..gui.motion_editor_scene import FrameBlockItem
from ..gui.motion_editor_scene import IfBlockItem
from ..gui.motion_editor_scene import StartBlockItem
from ..gui.motion_editor_scene import SwitchBlockItem


class AnimationPreviewVisualizer:
    def __init__(self, scene, trajectory_visualizer, frame_loader):
        self.scene = scene  # MotionFlowScene
        self.visualizer = trajectory_visualizer  # TrajectoryVisualizer
        self.load_frame = frame_loader  # Callable: frame_name -> (JointState, move_duration, wait_duration)

        self._thread = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._lock = threading.Lock()

        self.current_block = None
        self.next_block = None
        self.state = 'stopped'

        self._prev_snapshot = self._get_scene_snapshot()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._pause_event.clear()
        self.state = 'playing'
        self._prev_snapshot = self._get_scene_snapshot()  # snapshotを記録
        self._thread = threading.Thread(target=self._run)
        self._thread.start()

    def pause(self):
        with self._lock:
            self.state = 'paused'
            self._pause_event.set()

    def resume(self):
        with self._lock:
            self.state = 'playing'
            self._pause_event.clear()

    def stop(self):
        self._stop_event.set()
        self._pause_event.set()
        self.state = 'stopped'
        if self._thread:
            self._thread.join()

    def update_scene(self, new_scene):
        self.scene = new_scene

    def _get_scene_snapshot(self):
        snapshot = {}
        for block_id, block in self.scene.block_objects.items():
            entry = {
                'type': type(block).__name__,
                'filename': getattr(block, 'filename', ''),
                'preview_output_index': getattr(block, 'preview_output_index', None),
                'num_outputs': len(getattr(block, 'output_arrows', [])),
            }
            if hasattr(block, 'output_sub_blocks'):
                entry['subblock_keys'] = sorted(block.output_sub_blocks.keys())
            snapshot[block_id] = entry
        return snapshot

    def _scene_changed(self):
        current = self._get_scene_snapshot()
        if set(current.keys()) != set(self._prev_snapshot.keys()):
            return True
        for block_id in current:
            curr = current[block_id]
            prev = self._prev_snapshot.get(block_id)
            if not prev:
                return True
            for key in curr:
                if key == "preview_output_index":
                    continue  # preview index の変更は許容
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

        if isinstance(block, (IfBlockItem, SwitchBlockItem)):
            outputs = list(block.output_sub_blocks.values())
            idx = block.preview_output_index
            if 0 <= idx < len(outputs):
                sub = outputs[idx]
                if sub.output_arrows:
                    return sub.output_arrows[0].end_item
            return None

        if isinstance(block, StartBlockItem):
            return block.output_arrows[0].end_item if block.output_arrows else None

        return None

    def _run(self):
        self.current_block = self._get_start_block()
        self.next_block = self._get_next_block(self.current_block)
        start_time = time.perf_counter()

        while self.current_block and not self._stop_event.is_set():
            if self.state == 'paused':
                self._pause_event.wait()

            if self._scene_changed():
                print("[AnimationPreviewVisualizer] Scene structure changed. Stopping playback.")
                self.stop()
                return

            if not isinstance(self.current_block, FrameBlockItem):
                break

            frame_name = self.current_block.filename
            joint_state, move_duration, wait_duration = self.load_frame(frame_name)

            self.visualizer.publish_goal_state(joint_state)

            next_block = self._get_next_block(self.current_block)
            self.next_block = next_block  # 分岐変更に対応

            duration = move_duration + wait_duration
            while time.perf_counter() - start_time < duration:
                if self._stop_event.is_set() or self.state == 'paused':
                    break
                time.sleep(0.0001)  # 0.1ms 高精度sleep

            self.current_block = next_block
            start_time = time.perf_counter()
