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

from ..logic.frame_file_manager import FrameData
from ..logic.frame_file_manager import FrameFileManager
from ..robot_interface.trajectory_commander import TrajectoryCommander
from ..visualizer.frame_visualizer import FrameVisualizer
from ..visualizer.trajectory_visualizer import TrajectoryVisualizer
from .feedback_expression_dialog import FeedbackExpressionDialog
from .pid_gain_editor import PIDGainEditorDialog


class FrameEditorDialog(QDialog):
    def __init__(
        self,
        joint_names,
        joint_limits,
        available_variables,
        frame_path=None,
        parent=None,
        trajectory_visualizer: TrajectoryVisualizer = None,
        trajectory_commander: TrajectoryCommander = None
    ):
        super().__init__(parent)
        self.setWindowTitle("Edit Frame")

        self.joint_names = joint_names
        self.joint_limits = joint_limits
        self.available_variables = available_variables
        self.frame_path = frame_path

        self.frame_data = FrameData()
        self.frame_data.set_joint_names(joint_names)

        self.joint_widgets = {}
        self.enable_checkbox_widgets = {}

        self.trajectory_visualizer = trajectory_visualizer
        self.trajectory_commander = trajectory_commander

        self.frame_visualizer = FrameVisualizer(trajectory_visualizer)

        self.init_ui()

        if frame_path and os.path.exists(frame_path):
            self.load_frame_from_file(frame_path)

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

        max_label_width = max(QLabel(j).sizeHint().width() for j in self.joint_names) if self.joint_names else 100

        for joint_name in self.joint_names:
            row = QHBoxLayout()

            enable_cb = QCheckBox()
            enable_cb.setChecked(self.frame_data.get_enable(joint_name))
            enable_cb.stateChanged.connect(
                lambda state, j=joint_name: self.frame_data.set_enable(
                    j, state == Qt.Checked))
            self.enable_checkbox_widgets[joint_name] = enable_cb

            label = QLabel(joint_name)
            label.setFixedWidth(max_label_width)

            lower_rad, upper_rad = self.joint_limits.get(joint_name, (-math.pi, math.pi))
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
        buttons.accepted.connect(self.save_frame)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def set_all_enable_checkboxes(self, state):
        checked = (state == Qt.Checked)
        for joint_name, cb in self.enable_checkbox_widgets.items():
            cb.blockSignals(True)
            cb.setChecked(checked)
            self.frame_data.set_enable(joint_name, checked)
            cb.blockSignals(False)

    def reset_all_positions(self):
        for slider, spin, _ in self.joint_widgets.values():
            slider.blockSignals(True)
            spin.blockSignals(True)
            slider.setValue(0)
            spin.setValue(0.0)
            slider.blockSignals(False)
            spin.blockSignals(False)

    def open_pid_dialog(self, joint_name, button):
        current = self.frame_data.get_pid(joint_name)
        dialog = PIDGainEditorDialog(joint_name, current, parent=self)
        if dialog.exec_() and dialog.result:
            self.frame_data.set_pid(joint_name, dialog.result)
            button.setStyleSheet("background-color: lightblue;" if any(v != 0.0 for v in dialog.result) else "")

    def open_feedback_dialog(self, joint_name, button):
        current = self.frame_data.get_feedback(joint_name)
        dialog = FeedbackExpressionDialog(joint_name, current, self.available_variables, parent=self)
        if dialog.exec_() and dialog.result is not None:
            self.frame_data.set_feedback(joint_name, dialog.result)
            button.setStyleSheet("background-color: lightblue;" if dialog.result.strip() else "")

    def load_frame_from_file(self, path):
        raw = FrameFileManager.load_dict(os.path.dirname(frame_path), os.path.basename(frame_path))
        self.frame_data.set_dict(raw)

        self.duration_spin.setValue(self.frame_data.move_duration)
        self.wait_spin.setValue(self.frame_data.wait_duration)

        for joint_name in self.frame_data.get_joint_names():
            if joint_name not in self.joint_widgets:
                print(f"[WARNING] Joint {joint_name} not found in joint widgets.")
                continue

            _, spin, vel_spin = self.joint_widgets[joint_name]
            spin.blockSignals(True)
            spin.setValue(math.degrees(self.frame_data.get_pose(joint_name)))
            spin.blockSignals(False)

            vel_spin.blockSignals(True)
            vel_spin.setValue(self.frame_data.get_velocity_scale(joint_name))
            vel_spin.blockSignals(False)

            self.enable_checkbox_widgets[joint_name].blockSignals(True)
            self.enable_checkbox_widgets[joint_name].setChecked(self.frame_data.get_enable(joint_name))
            self.enable_checkbox_widgets[joint_name].blockSignals(False)

        print(f"[INFO] Loaded frame data from file: {path}")

    def save_frame(self):
        if not self.frame_path:
            self.reject()
            return

        self.frame_data.move_duration = self.duration_spin.value()
        self.frame_data.wait_duration = self.wait_spin.value()

        for joint_name in self.joint_names:
            _, spin, vel_spin = self.joint_widgets[joint_name]
            self.frame_data.set_pose(joint_name, math.radians(spin.value()))
            self.frame_data.set_velocity_scale(joint_name, vel_spin.value())
            self.frame_data.set_enable(joint_name, self.enable_checkbox_widgets[joint_name].isChecked())

        FrameFileManager.save_dict(
            os.path.dirname(self.frame_path),
            self.frame_data.get_dict(),
            os.path.basename(self.frame_path)
        )
        self.accept()

    def handle_play_button(self):
        sender = self.sender()
        for btn in [self.play_in_current_btn, self.play_in_current_out_btn, self.play_current_out_btn]:
            if btn != sender:
                btn.setChecked(False)
        if not self.loop_checkbox.isChecked():
            sender.setChecked(False)

        import rospy
        from sensor_msgs.msg import JointState

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
