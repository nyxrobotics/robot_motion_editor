
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

from ..logic.initial_pose_file_manager import load_initial_pose
from ..logic.initial_pose_file_manager import save_initial_pose
from ..visualizer.initial_pose_visualizer import InitialPoseVisualizer
from ..visualizer.trajectory_visualizer import TrajectoryVisualizer
from .feedback_expression_dialog import FeedbackExpressionDialog
from .pid_gain_editor import PIDGainEditorDialog


class InitialPoseEditor(QWidget):
    pose_updated = pyqtSignal()

    def __init__(self, joint_names, joint_limits, available_variables,
                 motion_directory=None, trajectory_visualizer: TrajectoryVisualizer = None):
        super().__init__()
        self.joint_names = joint_names
        self.joint_limits = joint_limits
        self.available_variables = available_variables
        self.motion_directory = motion_directory
        self.initial_pose_visualizer = InitialPoseVisualizer(joint_names, trajectory_visualizer)

        self.joint_widgets = {}
        self.enable_checkboxes = {}
        self.pid_config = {}
        self.feedback_expressions = {}
        self.prev_pose = []

        self.init_ui()

    def set_motion_directory(self, directory):
        self.motion_directory = directory
        self.load_pose()

    def init_ui(self):
        main_layout = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)

        # Header row with All Enable, Reload, Save
        header_layout = QHBoxLayout()
        self.all_enable_checkbox = QCheckBox("All Enable")
        self.all_enable_checkbox.stateChanged.connect(self.set_all_enable_checkboxes)
        header_layout.addWidget(self.all_enable_checkbox)

        reload_button = QPushButton("Reload")
        reload_button.clicked.connect(lambda: self.load_pose())
        header_layout.addWidget(reload_button)

        save_button = QPushButton("Save")
        save_button.clicked.connect(lambda: self.save_pose())
        header_layout.addWidget(save_button)
        layout.addLayout(header_layout)

        max_label_width = QLabel(max(self.joint_names, key=len)).sizeHint().width() if self.joint_names else 80

        for joint in self.joint_names:
            row = QHBoxLayout()

            enable_cb = QCheckBox()
            enable_cb.setChecked(True)
            enable_cb.stateChanged.connect(self.update_all_enable_checkbox)
            self.enable_checkboxes[joint] = enable_cb

            label = QLabel(joint)
            label.setFixedWidth(max_label_width)

            slider = QSlider(Qt.Horizontal)
            slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            spin = QDoubleSpinBox()
            spin.setDecimals(1)
            spin.setSingleStep(1.0)

            lower, upper = self.joint_limits.get(joint, (-math.pi, math.pi))
            lower_deg, upper_deg = math.degrees(lower), math.degrees(upper)

            slider.setRange(int(lower_deg), int(upper_deg))
            spin.setRange(lower_deg, upper_deg)

            slider.valueChanged.connect(lambda val, s=spin: s.setValue(float(val)))
            spin.valueChanged.connect(lambda val, sl=slider: sl.setValue(int(round(val))))
            spin.valueChanged.connect(self.on_pose_changed)

            pid_button = QPushButton("PID")
            pid_button.setFixedWidth(50)
            pid_button.clicked.connect(lambda _, j=joint, b=pid_button: self.open_pid_dialog(j, b))

            fb_button = QPushButton("FB")
            fb_button.setFixedWidth(50)
            fb_button.clicked.connect(lambda _, j=joint, b=fb_button: self.open_feedback_dialog(j, b))

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

    def set_motion_directory(self, directory):
        self.motion_directory = directory
        self.load_pose()

    def load_pose(self, filename="initial_pose.yaml"):
        if not self.motion_directory:
            rospy.logwarn("No path specified for loading pose.")
            return
        joint_data = load_initial_pose(self.motion_directory, filename)

        for joint, data in joint_data.items():
            if joint not in self.joint_widgets:
                continue
            pos_deg = math.degrees(data.get("position", 0.0))
            _, spin = self.joint_widgets[joint]
            spin.setValue(pos_deg)

            enable = data.get("enable", True)
            self.enable_checkboxes[joint].setChecked(enable)

            self.pid_config[joint] = tuple(data.get("pid", [0.0, 0.0, 0.0]))
            self.feedback_expressions[joint] = data.get("feedback", "")

        # Set the initial pose in the visualizer
        joint_state = JointState()
        for joint in self.joint_names:
            joint_state.name.append(joint)
            joint_state.position.append(joint_data[joint]["position"])
        self.initial_pose_visualizer.set_start_pose(joint_state)

    def save_pose(self, filename="initial_pose.yaml"):
        if not self.motion_directory:
            rospy.logwarn("No path specified for saving pose.")
            return
        joint_data = {}
        for joint in self.joint_names:
            _, spin = self.joint_widgets[joint]
            pos_rad = math.radians(spin.value())
            joint_data[joint] = {
                "position": pos_rad,
                "enable": self.enable_checkboxes[joint].isChecked(),
                "pid": list(self.pid_config.get(joint, (0.0, 0.0, 0.0))),
                "feedback": str(self.feedback_expressions.get(joint, "")).strip()
            }
        save_initial_pose(self.motion_directory, joint_data, filename)

        # Set the initial pose in the visualizer
        joint_state = JointState()
        for joint in self.joint_names:
            joint_state.name.append(joint)
            joint_state.position.append(joint_data[joint]["position"])
        self.initial_pose_visualizer.set_start_pose(joint_state)

    def get_target_joints(self):
        return [math.radians(self.joint_widgets[j][1].value()) for j in self.joint_names]

    def on_pose_changed(self):
        if not self.isVisible():
            return
        current = self.get_target_joints()
        if current != self.prev_pose:
            self.prev_pose = current
            msg = JointState()
            msg.name = self.joint_names
            msg.position = current
            self.initial_pose_visualizer.set_target_pose(msg)

    def update_all_enable_checkbox(self):
        checked = [cb.isChecked() for cb in self.enable_checkboxes.values()]
        total = len(checked)
        count = sum(checked)
        self.all_enable_checkbox.blockSignals(True)
        if count == total:
            self.all_enable_checkbox.setCheckState(Qt.Checked)
        elif count == 0:
            self.all_enable_checkbox.setCheckState(Qt.Unchecked)
        else:
            self.all_enable_checkbox.setTristate(True)
            self.all_enable_checkbox.setCheckState(Qt.PartiallyChecked)
        self.all_enable_checkbox.blockSignals(False)

    def set_all_enable_checkboxes(self, state):
        checked = state == Qt.Checked
        for cb in self.enable_checkboxes.values():
            cb.blockSignals(True)
            cb.setChecked(checked)
            cb.blockSignals(False)

    def open_pid_dialog(self, joint, button):
        current = self.pid_config.get(joint, (0.0, 0.0, 0.0))
        dialog = PIDGainEditorDialog(joint, current, parent=self)
        if dialog.exec_() and dialog.result:
            self.pid_config[joint] = dialog.result
            color = "lightblue" if any(dialog.result) else ""
            button.setStyleSheet(f"background-color: {color};")
            rospy.loginfo(f"Updated PID for {joint}: {dialog.result}")

    def open_feedback_dialog(self, joint, button):
        current = self.feedback_expressions.get(joint, "")
        dialog = FeedbackExpressionDialog(joint, current, self.available_variables, parent=self)
        if dialog.exec_() and dialog.result is not None:
            expr = dialog.result.strip()
            self.feedback_expressions[joint] = expr
            button.setStyleSheet("background-color: lightblue" if expr else "")
            rospy.loginfo(f"Updated Feedback expression for {joint}: {expr}")
