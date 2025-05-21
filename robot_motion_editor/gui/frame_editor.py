import math
import os
from dataclasses import dataclass
from dataclasses import field
from typing import Dict
from typing import List

import yaml
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

from ..visualizer.frame_visualizer import FrameVisualizer
from ..visualizer.trajectory_visualizer import TrajectoryVisualizer
from .feedback_expression_dialog import FeedbackExpressionDialog
from .pid_config_dialog import PIDConfigDialog


@dataclass
class JointCommand:
    position: float = 0.0  # in radians
    velocity_scale: float = 1.0
    enable: bool = True
    pid: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    feedback: str = ""


@dataclass
class FrameData:
    move_duration: float = 2.0
    wait_duration: float = 0.0
    joints: Dict[str, JointCommand] = field(default_factory=dict)

    def to_dict(self):
        joints_dict = {}
        velocity_scale_dict = {}

        for name, cmd in self.joints.items():
            joints_dict[name] = {
                "position": cmd.position,
                "pid": cmd.pid,
                "enable": cmd.enable,
                "feedback": cmd.feedback
            }
            velocity_scale_dict[name] = cmd.velocity_scale

        return {
            "joints": joints_dict,
            "time": {
                "move_duration": self.move_duration,
                "wait_duration": self.wait_duration
            },
            "velocity_scale": velocity_scale_dict
        }


class FrameFileManager:
    @staticmethod
    def load(path: str, joint_names: List[str]) -> FrameData:
        try:
            with open(path, "r") as f:
                raw = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"[FrameFileManager] Failed to load: {e}")
            return FrameData()

        joints_raw = raw.get("joints", {})
        velocity_raw = raw.get("velocity_scale", {})

        frame = FrameData(
            move_duration=raw.get("time", {}).get("move_duration", 2.0),
            wait_duration=raw.get("time", {}).get("wait_duration", 0.0),
        )

        for joint_name in joint_names:
            j = joints_raw.get(joint_name, {})
            vscale = velocity_raw.get(joint_name, 1.0)
            frame.joints[joint_name] = JointCommand(
                position=j.get("position", 0.0),
                velocity_scale=vscale,
                enable=j.get("enable", True),
                pid=j.get("pid", [0.0, 0.0, 0.0]),
                feedback=j.get("feedback", "")
            )

        return frame

    @staticmethod
    def save(path: str, frame_data: FrameData) -> None:
        output = {
            "time": {
                "move_duration": frame_data.move_duration,
                "wait_duration": frame_data.wait_duration
            },
            "velocity_scale": {},
            "joints": {}
        }

        for joint_name, cmd in frame_data.joints.items():
            output["velocity_scale"][joint_name] = cmd.velocity_scale
            output["joints"][joint_name] = {
                "position": cmd.position,
                "enable": cmd.enable,
                "pid": cmd.pid,
                "feedback": cmd.feedback
            }

        try:
            with open(path, "w") as f:
                yaml.safe_dump(output, f, allow_unicode=True)
        except Exception as e:
            print(f"[FrameFileManager] Failed to save: {e}")


class FrameEditorDialog(QDialog):
    def __init__(
        self,
        joint_names,
        joint_limits,
        available_variables,
        frame_path=None,
        parent=None,
        trajectory_visualizer: TrajectoryVisualizer = None
    ):
        super().__init__(parent)
        self.setWindowTitle("Edit Frame")

        self.joint_names = joint_names
        self.joint_limits = joint_limits
        self.available_variables = available_variables
        self.frame_path = frame_path

        self.frame_data = FrameData(
            move_duration=2.0,
            wait_duration=0.0,
            joints={name: JointCommand() for name in joint_names}
        )

        if frame_path and os.path.exists(frame_path):
            loaded = FrameFileManager.load(frame_path, joint_names)
            if not joint_names and loaded and loaded.joints:
                joint_names = list(loaded.joints.keys())
            elif loaded and loaded.joints:
                for name in loaded.joints:
                    if name not in joint_names:
                        joint_names.append(name)

        self.joint_widgets = {}
        self.enable_checkbox_widgets = {}

        self.trajectory_visualizer = trajectory_visualizer
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
            cmd = self.frame_data.joints[joint_name]

            enable_cb = QCheckBox()
            enable_cb.setChecked(cmd.enable)
            enable_cb.stateChanged.connect(lambda state, j=joint_name: self.update_enable(j, state))
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
            vel_spin.setValue(cmd.velocity_scale)
            vel_spin.valueChanged.connect(
                lambda val, j=joint_name: self.frame_data.joints[j].__setattr__(
                    "velocity_scale", val))

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

    def update_enable(self, joint_name, state):
        self.frame_data.joints[joint_name].enable = (state == Qt.Checked)

    def set_all_enable_checkboxes(self, state):
        checked = (state == Qt.Checked)
        for joint_name, cb in self.enable_checkbox_widgets.items():
            cb.blockSignals(True)
            cb.setChecked(checked)
            self.frame_data.joints[joint_name].enable = checked
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
        current = self.frame_data.joints[joint_name].pid
        dialog = PIDConfigDialog(joint_name, current, parent=self)
        if dialog.exec_() and dialog.result:
            self.frame_data.joints[joint_name].pid = dialog.result
            button.setStyleSheet("background-color: lightblue;" if any(v != 0.0 for v in dialog.result) else "")

    def open_feedback_dialog(self, joint_name, button):
        current = self.frame_data.joints[joint_name].feedback
        dialog = FeedbackExpressionDialog(joint_name, current, self.available_variables, parent=self)
        if dialog.exec_() and dialog.result is not None:
            self.frame_data.joints[joint_name].feedback = dialog.result
            button.setStyleSheet("background-color: lightblue;" if dialog.result.strip() else "")

    def load_frame_from_file(self, path):
        self.frame_data = FrameFileManager.load(path, self.joint_names)
        self.duration_spin.setValue(self.frame_data.move_duration)
        self.wait_spin.setValue(self.frame_data.wait_duration)

        for joint_name, cmd in self.frame_data.joints.items():
            if joint_name not in self.joint_widgets:
                continue
            _, spin, vel_spin = self.joint_widgets[joint_name]
            spin.setValue(math.degrees(cmd.position))
            vel_spin.setValue(cmd.velocity_scale)
            self.enable_checkbox_widgets[joint_name].setChecked(cmd.enable)

    def save_frame(self):
        if not self.frame_path:
            self.reject()
            return

        self.frame_data.move_duration = self.duration_spin.value()
        self.frame_data.wait_duration = self.wait_spin.value()

        for joint_name in self.joint_names:
            _, spin, vel_spin = self.joint_widgets[joint_name]
            self.frame_data.joints[joint_name].position = math.radians(spin.value())
            self.frame_data.joints[joint_name].velocity_scale = vel_spin.value()
            self.frame_data.joints[joint_name].enable = self.enable_checkbox_widgets[joint_name].isChecked()

        FrameFileManager.save(self.frame_path, self.frame_data)
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
        msg = JointState()
        msg.name = []
        msg.position = []
        for joint_name in self.joint_names:
            cmd = self.frame_data.joints[joint_name]
            if cmd.enable:
                msg.name.append(joint_name)
                msg.position.append(cmd.position)

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
        import rospy
        from sensor_msgs.msg import JointState
        msg = JointState()
        msg.name = []
        msg.position = []
        for joint_name in self.joint_names:
            cmd = self.frame_data.joints[joint_name]
            if cmd.enable:
                _, spin, _ = self.joint_widgets[joint_name]
                cmd.position = math.radians(spin.value())
                msg.name.append(joint_name)
                msg.position.append(cmd.position)
        msg.header.stamp = rospy.Time.now()
        self.trajectory_visualizer.publish_goal_state(msg)

    def accept(self):
        with open(self.frame_path, "w") as f:
            yaml.dump(self.frame_data.to_dict(), f)

        print(f"[INFO] Frame saved to {self.frame_path}")
        super().accept()
