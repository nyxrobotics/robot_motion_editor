import math

import rospy
from PyQt5.QtCore import Qt
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QCheckBox
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
        self.motion_directory = None
        self.joint_names = joint_names
        self.joint_limits = joint_limits
        self.available_variables = available_variables

        self.joint_widgets = {}
        self.joint_enabled = {}
        self.enable_checkbox_widgets = {}
        self.pid_config = {}
        self.feedback_expressions = {}
        self.prev_pose = []
        self.visualizer = InitialPoseVisualizer(joint_names)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)

        # Save + All Enable row
        save_row = QHBoxLayout()
        self.all_enable_checkbox = QCheckBox("All Enable")
        self.all_enable_checkbox.stateChanged.connect(self.set_all_enable_checkboxes)
        save_row.addWidget(self.all_enable_checkbox)

        save_button = QPushButton("Save Initial Pose")
        save_button.clicked.connect(self.save_pose_to_file)
        save_row.addWidget(save_button)
        layout.addLayout(save_row)

        max_label = QLabel(max(self.joint_names, key=len))
        max_label_width = max_label.sizeHint().width()

        for joint in self.joint_names:
            row = QHBoxLayout()

            enable_cb = QCheckBox()
            enable_cb.setChecked(True)
            enable_cb.stateChanged.connect(self.update_all_enable_checkbox)
            self.enable_checkbox_widgets[joint] = enable_cb
            self.joint_enabled[joint] = True

            label = QLabel(joint)
            label.setFixedWidth(max_label_width)

            slider = QSlider(Qt.Horizontal)
            slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            spin = QDoubleSpinBox()
            spin.setDecimals(1)
            spin.setSingleStep(1.0)

            lower_rad, upper_rad = self.joint_limits.get(joint, (-math.pi, math.pi))
            lower_deg = math.degrees(lower_rad)
            upper_deg = math.degrees(upper_rad)

            slider.setRange(int(lower_deg), int(upper_deg))
            spin.setRange(lower_deg, upper_deg)

            slider.valueChanged.connect(lambda val, s=spin: s.setValue(float(val)))
            spin.valueChanged.connect(lambda val, sl=slider: sl.setValue(int(round(val))))
            spin.valueChanged.connect(self.on_pose_changed)

            pid_button = QPushButton("PID")
            pid_button.setFixedWidth(50)
            pid_button.clicked.connect(lambda _, j=joint, btn=pid_button: self.open_pid_dialog(j, btn))

            fb_button = QPushButton("FB")
            fb_button.setFixedWidth(50)
            fb_button.clicked.connect(lambda _, j=joint, btn=fb_button: self.open_feedback_dialog(j, btn))

            row.addWidget(enable_cb)
            row.addWidget(label)
            row.addWidget(slider)
            row.addWidget(spin)
            row.addWidget(pid_button)
            row.addWidget(fb_button)
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
        self.motion_directory = directory
        self.load_pose_if_exists()

    def save_pose_to_file(self):
        positions = self.get_target_joints()
        if self.motion_directory:
            save_initial_pose(self.motion_directory, self.joint_names, positions)
            rospy.loginfo("Initial pose saved.")

    def load_pose_if_exists(self):
        if not self.motion_directory:
            return
        loaded = load_initial_pose(self.motion_directory)
        if not loaded:
            return

        for name, rad in loaded.items():
            deg = math.degrees(rad)
            if name in self.joint_widgets:
                _, spin = self.joint_widgets[name]
                spin.setValue(deg)

    def set_all_enable_checkboxes(self, state):
        checked = state == Qt.Checked
        for joint, checkbox in self.enable_checkbox_widgets.items():
            checkbox.blockSignals(True)
            checkbox.setChecked(checked)
            self.joint_enabled[joint] = checked
            checkbox.blockSignals(False)

    def update_all_enable_checkbox(self):
        checked_count = sum(cb.isChecked() for cb in self.enable_checkbox_widgets.values())
        total = len(self.enable_checkbox_widgets)
        if checked_count == total:
            self.all_enable_checkbox.blockSignals(True)
            self.all_enable_checkbox.setCheckState(Qt.Checked)
            self.all_enable_checkbox.blockSignals(False)
        elif checked_count == 0:
            self.all_enable_checkbox.blockSignals(True)
            self.all_enable_checkbox.setCheckState(Qt.Unchecked)
            self.all_enable_checkbox.blockSignals(False)
        else:
            self.all_enable_checkbox.blockSignals(True)
            self.all_enable_checkbox.setTristate(True)
            self.all_enable_checkbox.setCheckState(Qt.PartiallyChecked)
            self.all_enable_checkbox.blockSignals(False)

    def open_pid_dialog(self, joint_name, button):
        current = self.pid_config.get(joint_name, (0.0, 0.0, 0.0))
        dialog = PIDConfigDialog(joint_name, current, parent=self)
        if dialog.exec_() and dialog.result:
            self.pid_config[joint_name] = dialog.result
            p, i, d = dialog.result
            if any(val != 0.0 for val in (p, i, d)):
                button.setStyleSheet("background-color: lightblue;")
            else:
                button.setStyleSheet("")
            rospy.loginfo(f"Updated PID for {joint_name}: {dialog.result}")

    def open_feedback_dialog(self, joint_name, button):
        current_expr = self.feedback_expressions.get(joint_name, "")
        dialog = FeedbackExpressionDialog(
            joint_name, current_expr, self.available_variables, parent=self
        )
        if dialog.exec_() and dialog.result is not None:
            self.feedback_expressions[joint_name] = dialog.result
            if dialog.result.strip():
                button.setStyleSheet("background-color: lightblue;")
            else:
                button.setStyleSheet("")
            rospy.loginfo(f"Updated Feedback expression for {joint_name}: {dialog.result}")
