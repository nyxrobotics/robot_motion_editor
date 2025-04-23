from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDoubleSpinBox
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QSlider
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
            spin = QDoubleSpinBox()
            spin.setDecimals(1)
            spin.setSingleStep(1.0)
            spin.setRange(-180.0, 180.0)

            slider.valueChanged.connect(lambda val, s=spin: s.setValue(float(val)))
            spin.valueChanged.connect(lambda val, sl=slider: sl.setValue(int(round(val))))

            row.addWidget(label)
            row.addWidget(slider)
            row.addWidget(spin)
            layout.addLayout(row)

        self.setLayout(layout)
