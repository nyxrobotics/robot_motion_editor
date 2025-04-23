from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDoubleSpinBox
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QScrollArea
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtWidgets import QSlider
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget


class InitialPoseEditor(QWidget):
    def __init__(self, joint_names):
        super().__init__()
        self.joint_names = joint_names
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Create a scrollable area for joint sliders
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)

        # Add Save Initial Pose button at the top
        save_button = QPushButton("Save Initial Pose")
        layout.addWidget(save_button)

        # Determine the maximum width of the joint name labels
        max_label = QLabel(max(self.joint_names, key=len))
        max_label_width = max_label.sizeHint().width()

        for joint in self.joint_names:
            row = QHBoxLayout()
            label = QLabel(joint)
            label.setFixedWidth(max_label_width)

            slider = QSlider(Qt.Horizontal)
            slider.setRange(-180, 180)
            slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

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

        scroll.setWidget(content)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)
