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
        self.load_frame = frame_loader  # 関数: frame_name -> (JointState, move_duration, wait_duration)

        self._thread = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._lock = threading.Lock()

        self.current_block = None
        self.next_block = None
        self.state = 'stopped'  # 'playing', 'paused', 'stopped'

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._pause_event.clear()
        self.state = 'playing'
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

    def _run(self):
        self.current_block = self._get_start_block()
        self.next_block = self._get_next_block(self.current_block)
        start_time = time.perf_counter()
        while self.current_block and not self._stop_event.is_set():
            if self.state == 'paused':
                self._pause_event.wait()

            if not isinstance(self.current_block, FrameBlockItem):
                break

            frame_name = self.current_block.filename
            joint_state, move_duration, wait_duration = self.load_frame(frame_name)

            self.visualizer.publish_goal_state(joint_state)

            # 事前に次のブロックをセット
            next_block = self._get_next_block(self.current_block)
            self.next_block = next_block  # 分岐変更されていても追従

            # 高精度スリープ
            duration = move_duration + wait_duration
            while time.perf_counter() - start_time < duration:
                if self._stop_event.is_set() or self.state == 'paused':
                    break
                time.sleep(0.0001)
            self.current_block = next_block
            start_time = time.perf_counter()

    def _get_start_block(self):
        for block in self.scene.block_objects.values():
            if isinstance(block, StartBlockItem):
                return self._get_next_block(block)
        return None

    def _get_next_block(self, block):
        # Frame → output_arrows → next
        if isinstance(block, FrameBlockItem):
            if block.output_arrows:
                return block.output_arrows[0].end_item
            return None

        # If/Switch → preview index 経由
        if isinstance(block, (IfBlockItem, SwitchBlockItem)):
            outputs = list(block.output_sub_blocks.values())
            if outputs:
                idx = block.preview_output_index
                if idx < len(outputs):
                    sub = outputs[idx]
                    if sub.output_arrows:
                        return sub.output_arrows[0].end_item
            return None

        # Start → output_arrows[0].end_item
        if isinstance(block, StartBlockItem):
            if block.output_arrows:
                return block.output_arrows[0].end_item
        return None
