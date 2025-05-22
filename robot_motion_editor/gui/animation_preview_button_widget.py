import os

from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget

from ..logic.frame_file_manager import FrameData
from ..logic.frame_file_manager import FrameFileManager
from .animation_editor_widget import FrameBlockItem


class AnimationPreviewButtonWidget(QWidget):
    def __init__(self, preview_controller, parent=None):
        super().__init__(parent)
        self.controller = preview_controller  # AnimationVisualizer

        self.play_btn = QPushButton("▶ Play")
        self.pause_btn = QPushButton("❚❚ Pause")
        self.stop_btn = QPushButton("■ Stop")

        self.play_btn.clicked.connect(self.play)
        self.pause_btn.clicked.connect(self.pause)
        self.stop_btn.clicked.connect(self.stop)

        layout = QVBoxLayout()
        layout.addWidget(self.play_btn)
        layout.addWidget(self.pause_btn)
        layout.addWidget(self.stop_btn)
        self.setLayout(layout)

    def play(self):
        if self.controller.state == 'paused':
            self.controller.resume()
        else:
            selected_block = None
            for item in self.controller.scene.selectedItems():
                if hasattr(item, "output_arrows"):
                    selected_block = item
                    break
            self.controller.start(start_block=selected_block)

    def pause(self):
        if self.controller.state == 'playing':
            self.controller.pause()

        elif self.controller.state == 'stopped':
            selected = self.controller.scene.selectedItems()
            if len(selected) == 1 and isinstance(selected[0], FrameBlockItem):
                self.controller.play_single_block(selected[0])

    def stop(self):
        self.controller.stop()
