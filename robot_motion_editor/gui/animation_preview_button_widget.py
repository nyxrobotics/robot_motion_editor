from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget


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
            self.controller.start()

    def pause(self):
        self.controller.pause()

    def stop(self):
        self.controller.stop()
