import math
import os

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

from ..logic.initial_pose_file_manager import InitialPoseData
from ..logic.joint_data_manager import JointDataManager
from ..logic.motion_file_manager import MotionFileManager
from ..robot_interface.trajectory_commander import TrajectoryCommander
from ..visualizer.initial_pose_visualizer import InitialPoseVisualizer
from ..visualizer.trajectory_visualizer import TrajectoryVisualizer
from .feedback_expression_dialog import FeedbackExpressionDialog
from .pid_gain_editor import PIDGainEditorDialog


class InitialPoseEditor(QWidget):
    pose_updated = pyqtSignal()

    def __init__(self,
                 joint_data_manager: JointDataManager,
                 motion_file_manager: MotionFileManager,
                 trajectory_visualizer: TrajectoryVisualizer = None,
                 trajectory_commander: TrajectoryCommander = None):
        super().__init__()

        self.joint_data_manager = joint_data_manager
        self.motion_file_manager = motion_file_manager

        self.initial_pose_data = InitialPoseData()
        self.initial_pose_data.set_joint_names(self.joint_data_manager.get_joint_names())

        self.initial_pose_visualizer = InitialPoseVisualizer(
            self.joint_data_manager.get_joint_names(), trajectory_visualizer)
        self.trajectory_commander = trajectory_commander

        self.enable_checkboxes = {}
        self.joint_widgets = {}

        self.goal_pose = JointState()

        self.init_ui()

        if os.path.exists(self.motion_file_manager.resolve_initial_pose_path()):
            self.load_pose()

    def init_ui(self):
        main_layout = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)

        header_layout = QHBoxLayout()
        self.all_enable_checkbox = QCheckBox("All Enable")
        self.all_enable_checkbox.stateChanged.connect(self.set_all_enable_checkboxes)
        header_layout.addWidget(self.all_enable_checkbox)

        reload_button = QPushButton("Reload")
        reload_button.clicked.connect(self.load_pose)
        header_layout.addWidget(reload_button)

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_pose)
        header_layout.addWidget(save_button)

        layout.addLayout(header_layout)

        max_label_width = QLabel(max(self.initial_pose_data.get_joint_names(), key=len)
                                 ).sizeHint().width() if self.initial_pose_data.get_joint_names() else 80

        for joint_name in self.initial_pose_data.get_joint_names():
            row = QHBoxLayout()

            enable_cb = QCheckBox()
            enable_cb.setChecked(True)
            enable_cb.stateChanged.connect(self.update_all_enable_checkbox)
            self.enable_checkboxes[joint_name] = enable_cb

            label = QLabel(joint_name)
            label.setFixedWidth(max_label_width)

            slider = QSlider(Qt.Horizontal)
            slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            spin = QDoubleSpinBox()
            spin.setDecimals(1)
            spin.setSingleStep(1.0)

            lower, upper = self.joint_data_manager.get_joint_limit(joint_name)
            lower_deg, upper_deg = math.degrees(lower), math.degrees(upper)

            slider.setRange(int(lower_deg), int(upper_deg))
            spin.setRange(lower_deg, upper_deg)

            slider.valueChanged.connect(lambda val, s=spin: s.setValue(float(val)))
            spin.valueChanged.connect(lambda val, sl=slider: sl.setValue(int(round(val))))
            spin.valueChanged.connect(self.on_pose_changed)

            pid_button = QPushButton("PID")
            pid_button.setFixedWidth(50)
            pid_button.clicked.connect(lambda _, j=joint_name, b=pid_button: self.open_pid_dialog(j, b))

            fb_button = QPushButton("FB")
            fb_button.setFixedWidth(50)
            fb_button.clicked.connect(lambda _, j=joint_name, b=fb_button: self.open_feedback_dialog(j, b))

            row.addWidget(enable_cb)
            row.addWidget(label)
            row.addWidget(slider)
            row.addWidget(spin)
            row.addWidget(pid_button)
            row.addWidget(fb_button)
            layout.addLayout(row)

            self.joint_widgets[joint_name] = (slider, spin)

        scroll.setWidget(content)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

    def load_pose(self):
        self.initial_pose_data.load_from_file(self.motion_file_manager.resolve_initial_pose_path())

        for joint_name in self.initial_pose_data.get_joint_names():
            if joint_name not in self.joint_widgets:
                continue

            pos_deg = math.degrees(self.initial_pose_data.get_pose(joint_name))
            _, spin = self.joint_widgets[joint_name]
            spin.setValue(pos_deg)
            self.enable_checkboxes[joint_name].setChecked(self.initial_pose_data.get_enable(joint_name))

        if self.initial_pose_visualizer:
            self.initial_pose_visualizer.set_start_pose(self.initial_pose_data.get_joint_state())
        if self.trajectory_commander:
            self.trajectory_commander.send_joint_state(self.initial_pose_data.get_joint_state(), duration=1.0)

    def save_pose(self):
        for joint_name in self.initial_pose_data.get_joint_names():
            _, spin = self.joint_widgets[joint_name]
            position_rad = math.radians(spin.value())
            self.initial_pose_data.set_pose(joint_name, position_rad)
            self.initial_pose_data.set_enable(joint_name, self.enable_checkboxes[joint_name].isChecked())

        self.initial_pose_data.save_to_file(self.motion_file_manager.resolve_initial_pose_path())
        self.initial_pose_visualizer.set_start_pose(self.initial_pose_data.get_joint_state())

    def get_gui_joints(self):
        joint_msg = JointState()
        joint_msg.name = self.initial_pose_data.get_joint_names()
        joint_msg.position = [math.radians(self.joint_widgets[name][1].value())
                              for name in self.initial_pose_data.get_joint_names()]
        return joint_msg

    def on_pose_changed(self):
        if not self.isVisible():
            return
        next_goal_pose = self.get_gui_joints()
        if next_goal_pose != self.goal_pose:
            self.goal_pose = next_goal_pose
            if self.initial_pose_visualizer:
                self.initial_pose_visualizer.set_goal_pose(self.goal_pose)
            if self.trajectory_commander:
                self.trajectory_commander.send_joint_state(self.goal_pose, duration=1.0)

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
        for joint_name, cb in self.enable_checkboxes.items():
            cb.blockSignals(True)
            cb.setChecked(checked)
            self.initial_pose_data.set_enable(joint_name, checked)
            cb.blockSignals(False)

    def open_pid_dialog(self, joint_name: str, button):
        current = self.initial_pose_data.get_pid(joint_name)
        dialog = PIDGainEditorDialog(joint_name, current, parent=self)
        if dialog.exec_() and dialog.result:
            self.initial_pose_data.set_pid(joint_name, dialog.result)
            button.setStyleSheet("background-color: lightblue" if any(dialog.result) else "")
            rospy.loginfo(f"Updated PID for {joint_name}: {dialog.result}")

    def open_feedback_dialog(self, joint_name: str, button):
        current = self.initial_pose_data.get_feedback(joint_name)
        dialog = FeedbackExpressionDialog(
            joint_name,
            current,
            self.joint_data_manager.get_available_variables(),
            parent=self)
        if dialog.exec_() and dialog.result is not None:
            expr = dialog.result.strip()
            self.initial_pose_data.set_feedback(joint_name, expr)
            button.setStyleSheet("background-color: lightblue" if expr else "")
            rospy.loginfo(f"Updated Feedback expression for {joint_name}: {expr}")
