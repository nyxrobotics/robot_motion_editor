from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QSlider
from PyQt5.QtWidgets import QSpinBox
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget


class InitialPoseEditor(QWidget):
    def __init__(self, joint_names):
        super().__init__()
        self.joint_names = joint_names
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        for joint in self.joint_names:
            row = QHBoxLayout()
            label = QLabel(joint)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(-180, 180)
            spin = QSpinBox()
            spin.setRange(-180, 180)

            slider.valueChanged.connect(spin.setValue)
            spin.valueChanged.connect(slider.setValue)

            row.addWidget(label)
            row.addWidget(slider)
            row.addWidget(spin)
            layout.addLayout(row)

        self.setLayout(layout)
