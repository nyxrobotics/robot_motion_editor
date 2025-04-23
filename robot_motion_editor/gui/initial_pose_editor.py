import math

import rospy
from PyQt5.QtCore import Qt
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDoubleSpinBox
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QScrollArea
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtWidgets import QSlider
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget
from sensor_msgs.msg import JointState

from .initial_pose_visualizer import InitialPoseVisualizer


class InitialPoseEditor(QWidget):
    pose_updated = pyqtSignal()

    def __init__(self, joint_names):
        super().__init__()
        self.joint_names = joint_names
        self.joint_widgets = {}  # {name: (slider, spin)}
        self.prev_pose = []
        self.visualizer = InitialPoseVisualizer(joint_names)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)

        save_button = QPushButton("Save Initial Pose")
        layout.addWidget(save_button)

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

            # Synchronize slider and spin box
            slider.valueChanged.connect(lambda val, s=spin: s.setValue(float(val)))
            spin.valueChanged.connect(lambda val, sl=slider: sl.setValue(int(round(val))))

            # Publish when value changes
            spin.valueChanged.connect(self.on_pose_changed)

            row.addWidget(label)
            row.addWidget(slider)
            row.addWidget(spin)
            layout.addLayout(row)

            self.joint_widgets[joint] = (slider, spin)

        scroll.setWidget(content)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

    def get_target_joints(self):
        positions = []
        for joint in self.joint_names:
            _, spin = self.joint_widgets[joint]
            degree = spin.value()
            radian = math.radians(degree)
            positions.append(radian)
        return positions

    def on_pose_changed(self):
        if self.isVisible():
            current = self.get_target_joints()
            if current != self.prev_pose:
                self.prev_pose = current
                msg = JointState()
                msg.name = self.joint_names
                msg.position = current
                self.visualizer.update_target_pose(msg)
                self.visualizer.publish_query_goal_state()
