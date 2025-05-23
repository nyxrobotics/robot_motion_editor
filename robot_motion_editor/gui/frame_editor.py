import math
import os

import rospy
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QDialogButtonBox
from PyQt5.QtWidgets import QDoubleSpinBox
from PyQt5.QtWidgets import QFormLayout
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QScrollArea
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtWidgets import QSlider
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget
from sensor_msgs.msg import JointState

from ..logic.frame_file_manager import FrameData
from ..logic.frame_file_manager import FrameFileManager
from ..logic.joint_data_manager import JointDataManager
from ..logic.motion_directory_manager import MotionDirectoryManager
from ..robot_interface.trajectory_commander import TrajectoryCommander
from ..visualizer.frame_visualizer import FrameVisualizer
from ..visualizer.trajectory_visualizer import TrajectoryVisualizer
from .feedback_expression_dialog import FeedbackExpressionDialog
from .pid_gain_editor import PIDGainEditorDialog


class FrameEditorDialog(QDialog):
    def __init__(
        self,
        joint_data_manager: JointDataManager,
        motion_directory_manager: MotionDirectoryManager,
        frame_name=None,
        trajectory_visualizer: TrajectoryVisualizer = None,
        trajectory_commander: TrajectoryCommander = None
    ):
        super().__init__()
        self.setWindowTitle("Edit Frame")

        self.joint_data_manager = joint_data_manager
        self.motion_directory_manager = motion_directory_manager
        self.frame_name = frame_name

        self.frame_data = FrameData()
        self.frame_data.set_joint_names(joint_data_manager.get_joint_names())

        self.joint_widgets = {}
        self.enable_checkbox_widgets = {}

        self.trajectory_visualizer = trajectory_visualizer
        self.trajectory_commander = trajectory_commander

        self.frame_visualizer = FrameVisualizer(trajectory_visualizer)

        self.init_ui()

        if frame_name:
            path = self.motion_directory_manager.resolve_frame_path(frame_name)
            if os.path.exists(path):
                self.frame_data.load_from_file(path)
                self.frame_path = path
            else:
                self.frame_path = self.motion_directory_manager.resolve_frame_path(frame_name)
        else:
            self.frame_path = None

    def init_ui(self):
        layout = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)

        playback_row = QHBoxLayout()
        self.loop_checkbox = QCheckBox("Loop")
        self.loop_checkbox.setChecked(False)
        self.loop_checkbox.stateChanged.connect(self.on_loop_checkbox_changed)
        playback_row.addWidget(self.loop_checkbox)

        self.play_in_current_btn = QPushButton("In-Current")
        self.play_in_current_out_btn = QPushButton("In-Current-Out")
        self.play_current_out_btn = QPushButton("Current-Out")

        for btn in [self.play_in_current_btn, self.play_in_current_out_btn, self.play_current_out_btn]:
            btn.setCheckable(True)
            btn.clicked.connect(self.handle_play_button)
            playback_row.addWidget(btn)

        form.addRow(playback_row)

        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setDecimals(2)
        self.duration_spin.setRange(0.0, 10.0)
        self.duration_spin.setSingleStep(0.1)

        self.wait_spin = QDoubleSpinBox()
        self.wait_spin.setDecimals(2)
        self.wait_spin.setRange(0.0, 10.0)
        self.wait_spin.setSingleStep(0.1)

        form.addRow("Move (sec)", self.duration_spin)
        form.addRow("Wait (sec)", self.wait_spin)

        all_enable_row = QHBoxLayout()
        self.all_enable_checkbox = QCheckBox("All Enable")
        self.all_enable_checkbox.stateChanged.connect(self.set_all_enable_checkboxes)
        all_enable_row.addWidget(self.all_enable_checkbox)

        self.reset_all_button = QPushButton("Reset All")
        self.reset_all_button.clicked.connect(self.reset_all_positions)
        all_enable_row.addWidget(self.reset_all_button)
        form.addRow(all_enable_row)

        joint_names = self.joint_data_manager.get_joint_names()
        max_label_width = max(QLabel(j).sizeHint().width() for j in joint_names) if joint_names else 100

        for joint_name in joint_names:
            row = QHBoxLayout()

            enable_cb = QCheckBox()
            enable_cb.setChecked(self.frame_data.get_enable(joint_name))
            enable_cb.stateChanged.connect(
                lambda state, j=joint_name: self.frame_data.set_enable(
                    j, state == Qt.Checked))
            self.enable_checkbox_widgets[joint_name] = enable_cb

            label = QLabel(joint_name)
            label.setFixedWidth(max_label_width)

            lower_rad, upper_rad = self.joint_data_manager.get_joint_limit(joint_name)
            lower_deg, upper_deg = math.degrees(lower_rad), math.degrees(upper_rad)

            slider = QSlider(Qt.Horizontal)
            slider.setRange(int(lower_deg), int(upper_deg))
            slider.setSingleStep(1)
            slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            spin = QDoubleSpinBox()
            spin.setDecimals(1)
            spin.setSingleStep(1.0)
            spin.setRange(lower_deg, upper_deg)

            slider.valueChanged.connect(
                lambda val,
                s=spin: (
                    s.setValue(
                        float(val)),
                    self.publish_goal_state_from_gui()))
            spin.valueChanged.connect(lambda val, sl=slider: (
                sl.setValue(int(round(val))), self.publish_goal_state_from_gui()))

            vel_spin = QDoubleSpinBox()
            vel_spin.setDecimals(2)
            vel_spin.setSingleStep(0.1)
            vel_spin.setRange(0.0, 5.0)
            vel_spin.setValue(self.frame_data.get_velocity_scale(joint_name))
            vel_spin.valueChanged.connect(lambda val, j=joint_name: self.frame_data.set_velocity_scale(j, val))

            pid_btn = QPushButton("PID")
            pid_btn.setFixedWidth(50)
            pid_btn.clicked.connect(lambda _, j=joint_name, btn=pid_btn: self.open_pid_dialog(j, btn))

            fb_btn = QPushButton("FB")
            fb_btn.setFixedWidth(50)
            fb_btn.clicked.connect(lambda _, j=joint_name, btn=fb_btn: self.open_feedback_dialog(j, btn))

            row.addWidget(enable_cb)
            row.addWidget(label)
            row.addWidget(slider)
            row.addWidget(spin)
            row.addWidget(QLabel("Vel"))
            row.addWidget(vel_spin)
            row.addWidget(pid_btn)
            row.addWidget(fb_btn)

            form.addRow(row)
            self.joint_widgets[joint_name] = (slider, spin, vel_spin)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def accept(self):
        if not self.frame_path:
            super().reject()
            return

        self.frame_data.move_duration = self.duration_spin.value()
        self.frame_data.wait_duration = self.wait_spin.value()

        for joint_name in self.joint_data_manager.get_joint_names():
            _, spin, vel_spin = self.joint_widgets[joint_name]
            self.frame_data.set_pose(joint_name, math.radians(spin.value()))
            self.frame_data.set_velocity_scale(joint_name, vel_spin.value())
            self.frame_data.set_enable(joint_name, self.enable_checkbox_widgets[joint_name].isChecked())

        self.frame_data.save_to_file(self.frame_path)
        super().accept()

    def handle_play_button(self):
        sender = self.sender()
        for btn in [self.play_in_current_btn, self.play_in_current_out_btn, self.play_current_out_btn]:
            if btn != sender:
                btn.setChecked(False)
        if not self.loop_checkbox.isChecked():
            sender.setChecked(False)

        msg = self.frame_data.get_joint_state()
        msg.header.stamp = rospy.Time.now()

        if self.trajectory_visualizer is None or self.frame_visualizer is None:
            rospy.logwarn("FrameVisualizer is not connected to TrajectoryVisualizer.")
            return

        self.trajectory_visualizer.publish_goal_state(msg)
        self.frame_visualizer.set_current_frame(msg, self.frame_data.move_duration, self.frame_data.wait_duration)

        if sender == self.play_in_current_btn:
            self.frame_visualizer.play_in_trajectory()
        elif sender == self.play_in_current_out_btn:
            self.frame_visualizer.play_in_out_trajectory()
        elif sender == self.play_current_out_btn:
            self.frame_visualizer.play_out_trajectory()

    def on_loop_checkbox_changed(self, state):
        if state == Qt.Unchecked:
            for btn in [self.play_in_current_btn, self.play_in_current_out_btn, self.play_current_out_btn]:
                btn.setChecked(False)

    def publish_goal_state_from_gui(self):
        for joint_name in self.joint_names:
            _, spin, _ = self.joint_widgets[joint_name]
            self.frame_data.set_pose(joint_name, math.radians(spin.value()))

        msg = self.frame_data.get_joint_state()
        msg.header.stamp = rospy.Time.now()

        if self.trajectory_visualizer:
            self.trajectory_visualizer.publish_goal_state(msg)

        if self.trajectory_commander:
            self.trajectory_commander.send_joint_state(msg, duration=1.0)
