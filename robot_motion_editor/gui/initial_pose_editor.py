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

from .feedback_expression_dialog import FeedbackExpressionDialog
from .initial_pose_file_manager import load_initial_pose
from .initial_pose_file_manager import save_initial_pose
from .initial_pose_visualizer import InitialPoseVisualizer
from .pid_config_dialog import PIDConfigDialog


class InitialPoseEditor(QWidget):
    pose_updated = pyqtSignal()

    def __init__(self, joint_names, joint_limits, available_variables):
        super().__init__()
        self.motion_directory = "."
        self.joint_names = joint_names
        self.joint_limits = joint_limits
        self.available_variables = available_variables
        self.joint_widgets = {}
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
        save_button.clicked.connect(self.save_pose_to_file)

        max_label = QLabel(max(self.joint_names, key=len))
        max_label_width = max_label.sizeHint().width()

        for joint in self.joint_names:
            row = QHBoxLayout()
            label = QLabel(joint)
            label.setFixedWidth(max_label_width)

            slider = QSlider(Qt.Horizontal)
            slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            spin = QDoubleSpinBox()
            spin.setDecimals(1)
            spin.setSingleStep(1.0)

            # Get joint limit and convert to degrees
            lower_rad, upper_rad = self.joint_limits.get(joint, (-math.pi, math.pi))
            lower_deg = math.degrees(lower_rad)
            upper_deg = math.degrees(upper_rad)

            slider.setRange(int(lower_deg), int(upper_deg))
            spin.setRange(lower_deg, upper_deg)

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

    def set_motion_directory(self, directory):
        """
        Set the motion directory and attempt to load the initial pose.
        """
        self.motion_directory = directory
        self.load_pose_if_exists()

    def save_pose_to_file(self):
        positions = self.get_target_joints()
        save_initial_pose(self.motion_directory, self.joint_names, positions)
        rospy.loginfo("Initial pose saved.")

    def load_pose_if_exists(self):
        loaded = load_initial_pose(self.motion_directory)
        if not loaded:
            rospy.logwarn(f"No initial pose file found in {self.motion_directory}")
            return

        for name, rad in loaded.items():
            deg = math.degrees(rad)
            if name in self.joint_widgets:
                _, spin = self.joint_widgets[name]
                spin.setValue(deg)

    def open_pid_dialog(self, joint_name):
        current = self.pid_config.get(joint_name, (0.0, 0.0, 0.0))
        dialog = PIDConfigDialog(joint_name, current, parent=self)
        if dialog.exec_() and dialog.result:
            self.pid_config[joint_name] = dialog.result
            rospy.loginfo(f"Updated PID for {joint_name}: {dialog.result}")

    def open_feedback_dialog(self, joint_name):
        current_expr = self.feedback_expressions.get(joint_name, "")
        variable_names = self.get_available_variables()
        dialog = FeedbackExpressionDialog(joint_name, current_expr, variable_names, parent=self)
        if dialog.exec_() and dialog.result:
            self.feedback_expressions[joint_name] = dialog.result
            rospy.loginfo(f"Updated Feedback expression for {joint_name}: {dialog.result}")
