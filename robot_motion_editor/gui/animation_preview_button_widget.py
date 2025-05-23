import os

from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget

from ..robot_interface.animation_commander import AnimationCommander
from ..visualizer.animation_visualizer import AnimationVisualizer
from .animation_editor_widget import FrameBlockItem


class AnimationPreviewButtonWidget(QWidget):
    def __init__(self, animation_visualizer: AnimationVisualizer = None,
                 animation_commander: AnimationCommander = None, parent=None):
        super().__init__(parent)
        self.animation_visualizer = animation_visualizer
        self.animation_commander = animation_commander

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
        selected_block = None
        for item in self.animation_visualizer.scene.selectedItems():
            if hasattr(item, "output_arrows"):
                selected_block = item
                break

        if self.animation_visualizer.state == 'paused':
            self.animation_visualizer.resume()
        else:
            self.animation_visualizer.start(start_block=selected_block)

        if self.animation_commander:
            if self.animation_commander.state == 'paused':
                self.animation_commander.resume()
            else:
                self.animation_commander.start(start_block=selected_block)

    def pause(self):
        if self.animation_visualizer.state == 'playing':
            self.animation_visualizer.pause()
        elif self.animation_visualizer.state == 'stopped':
            selected = self.animation_visualizer.scene.selectedItems()
            if len(selected) == 1:
                block = selected[0]
                self.animation_visualizer.play_single_block(block)

        if self.animation_commander and self.animation_commander.state == 'playing':
            self.animation_commander.pause()

    def stop(self):
        self.animation_visualizer.stop()
        if self.animation_commander:
            self.animation_commander.stop()
