import copy
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
from ..logic.initial_pose_file_manager import InitialPoseData
from ..logic.joint_data_manager import JointDataManager
from ..logic.motion_directory_manager import MotionDirectoryManager
from ..robot_interface.trajectory_commander import TrajectoryCommander
from ..visualizer.frame_visualizer import FrameVisualizer
from ..visualizer.trajectory_visualizer import TrajectoryVisualizer
from .animation_editor_items import FrameBlockItem
from .feedback_expression_dialog import FeedbackExpressionDialog
from .pid_gain_editor import PIDGainEditorDialog


class FrameEditorDialog(QDialog):
    def __init__(
        self,
        joint_data_manager: JointDataManager,
        motion_directory_manager: MotionDirectoryManager,
        filename: str = "",
        frame_block: FrameBlockItem = None,
        trajectory_visualizer: TrajectoryVisualizer = None,
        trajectory_commander: TrajectoryCommander = None,
        parent=None,
    ):
        super().__init__(parent)
        if parent is None:
            self.setWindowFlags(Qt.Window)

        # Core components
        self.joint_data_manager = joint_data_manager
        self.motion_directory_manager = motion_directory_manager
        self.trajectory_visualizer = trajectory_visualizer
        self.trajectory_commander = trajectory_commander
        self.frame_block = frame_block

        # Use filename from frame_block if available
        self.filename = frame_block.filename if frame_block else filename

        # Automatically detect the corresponding FrameBlockItem from animation_flow_scene
        # if frame_block is not explicitly provided
        if self.frame_block is None and self.animation_flow_scene and self.filename:
            matches = [
                b for b in self.animation_flow_scene.items()
                if isinstance(b, FrameBlockItem) and b.filename == self.filename
            ]
            if matches:
                # If multiple matches, use the first one found
                self.frame_block = matches[0]

        # Frame data initialization
        self.frame_data = FrameData()
        self.frame_data.set_joint_names(joint_data_manager.get_joint_names())
        self.joint_widgets = {}
        self.enable_checkbox_widgets = {}
        self.frame_visualizer = FrameVisualizer(trajectory_visualizer)

        self.init_ui()

        # Load frame data from file if it exists
        self.filepath = self.motion_directory_manager.resolve_frame_path(self.filename)
        if os.path.exists(self.filepath):
            self.frame_data.load_from_file(self.filepath)
            self.set_frame_to_ui()
            self.loaded_frame_data = copy.deepcopy(self.frame_data)
        else:
            self.loaded_frame_data = None
        self.setWindowTitle(f"Frame: {os.path.basename(self.filepath)}")

        # Set initial pose data to prev and next frames
        self.prev_frame_data = None
        self.next_frame_data = None
        path = self.motion_directory_manager.resolve_initial_pose_path()
        if os.path.exists(path):
            pose_data = InitialPoseData()
            pose_data.set_joint_names(self.joint_data_manager.get_joint_names())
            pose_data.load_from_file(path)
            frame = FrameData()
            frame.set_joint_names(self.joint_data_manager.get_joint_names())
            frame.set_joint_state(pose_data.get_joint_state())
            frame.move_duration = 1.0
            frame.wait_duration = 0.0
            self.prev_frame_data = frame
            self.next_frame_data = frame

    def init_ui(self):
        layout = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)

        playback_row = QHBoxLayout()
        self.loop_checkbox = QCheckBox("Loop")
        self.loop_checkbox.setChecked(True)
        self.loop_checkbox.stateChanged.connect(self.on_loop_checkbox_changed)
        playback_row.addWidget(self.loop_checkbox)

        self.play_previous_current_btn = QPushButton("Previous-Current")
        self.play_full_btn = QPushButton("Previous-Current-Next")
        self.play_current_next_btn = QPushButton("Current-Next")

        for btn in [self.play_previous_current_btn, self.play_full_btn, self.play_current_next_btn]:
            btn.setCheckable(True)
            btn.clicked.connect(self.handle_play_button)
            playback_row.addWidget(btn)

        form.addRow(playback_row)

        self.move_spin = QDoubleSpinBox()
        self.move_spin.setDecimals(2)
        self.move_spin.setRange(0.0, 10.0)
        self.move_spin.setSingleStep(0.1)

        self.wait_spin = QDoubleSpinBox()
        self.wait_spin.setDecimals(2)
        self.wait_spin.setRange(0.0, 10.0)
        self.wait_spin.setSingleStep(0.1)

        form.addRow("Move (sec)", self.move_spin)
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

    def focusInEvent(self, event):
        if self.trajectory_visualizer:
            self.trajectory_visualizer.enable()
        if self.trajectory_commander:
            self.trajectory_commander.enable()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        if self.trajectory_visualizer:
            self.trajectory_visualizer.disable()
        if self.trajectory_commander:
            self.trajectory_commander.disable()
        super().focusOutEvent(event)

    def set_all_enable_checkboxes(self, state):
        checked = (state == Qt.Checked)
        for joint_name, cb in self.enable_checkbox_widgets.items():
            cb.blockSignals(True)
            cb.setChecked(checked)
            self.frame_data.set_enable(joint_name, checked)
            cb.blockSignals(False)

    def reset_all_positions(self):
        try:
            path = self.motion_directory_manager.resolve_initial_frame_path()
            if os.path.exists(path):
                self.frame_data.load_from_file(path)
                self.set_frame_to_ui()
                return
        except Exception as e:
            rospy.logwarn(f"[FrameEditorDialog] Failed to reset from initial_frame.yaml: {e}")

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

    def handle_play_button(self):
        sender = self.sender()
        for btn in [self.play_previous_current_btn, self.play_full_btn, self.play_current_next_btn]:
            if btn != sender:
                btn.setChecked(False)
        if not self.loop_checkbox.isChecked():
            sender.setChecked(False)

        # Update current frame from GUI values
        self.frame_data.move_duration = self.move_spin.value()
        self.frame_data.wait_duration = self.wait_spin.value()
        for joint_name in self.joint_data_manager.get_joint_names():
            _, spin, vel_spin = self.joint_widgets[joint_name]
            self.frame_data.set_pose(joint_name, math.radians(spin.value()))
            self.frame_data.set_velocity_scale(joint_name, vel_spin.value())
            self.frame_data.set_enable(joint_name, self.enable_checkbox_widgets[joint_name].isChecked())

        current_frame = self.frame_data
        prev_frame = self._get_prev_frame_data()
        next_frame = self._get_next_frame_data()

        # Set frame data into visualizer
        self.frame_visualizer.set_previous_frame(
            prev_frame.get_joint_state(), prev_frame.move_duration, prev_frame.wait_duration)
        self.frame_visualizer.set_current_frame(
            current_frame.get_joint_state(), current_frame.move_duration, current_frame.wait_duration)
        self.frame_visualizer.set_next_frame(
            next_frame.get_joint_state(), next_frame.move_duration, next_frame.wait_duration)

        # Publish current frame goal state
        self.trajectory_visualizer.visualize_goal_state(current_frame.get_joint_state())

        # Execute playback
        if sender == self.play_previous_current_btn:
            self.frame_visualizer.play_previous_trajectory()
        elif sender == self.play_full_btn:
            self.frame_visualizer.play_full_trajectory()
        elif sender == self.play_current_next_btn:
            self.frame_visualizer.play_next_trajectory()

    def on_loop_checkbox_changed(self, state):
        loop_enabled = state == Qt.Checked

        # If loop is disabled, uncheck all play buttons (no persistent playback)
        if not loop_enabled:
            for btn in [self.play_previous_current_btn, self.play_full_btn, self.play_current_next_btn]:
                btn.setChecked(False)

        # Apply loop setting to trajectory visualizer
        if self.trajectory_visualizer:
            self.trajectory_visualizer.enable_loop(loop_enabled)

    def publish_goal_state_from_gui(self):
        for joint_name in self.frame_data.get_joint_names():
            _, spin, _ = self.joint_widgets[joint_name]
            self.frame_data.set_pose(joint_name, math.radians(spin.value()))

        msg = self.frame_data.get_joint_state()
        msg.header.stamp = rospy.Time.now()

        if self.trajectory_visualizer:
            self.trajectory_visualizer.visualize_goal_state(msg)
            if self.loaded_frame_data:
                self.frame_visualizer.set_previous_frame(
                    self.loaded_frame_data.get_joint_state(), 0.0, 0.0)
                self.frame_visualizer.set_current_frame(
                    self.frame_data.get_joint_state(), 1.0, 0.0)
                self.frame_visualizer.reset_next_frame()
                self.frame_visualizer.play_previous_trajectory()

        if self.trajectory_commander:
            self.trajectory_commander.send_joint_state(msg, duration=1.0)

    def set_frame_to_ui(self):
        self.move_spin.setValue(self.frame_data.move_duration)
        self.wait_spin.setValue(self.frame_data.wait_duration)
        for joint_name in self.frame_data.get_joint_names():
            if joint_name not in self.joint_widgets:
                continue
            slider, spin, vel_spin = self.joint_widgets[joint_name]

            deg = math.degrees(self.frame_data.get_pose(joint_name))
            spin.blockSignals(True)
            slider.blockSignals(True)
            spin.setValue(deg)
            slider.setValue(int(round(deg)))
            spin.blockSignals(False)
            slider.blockSignals(False)

            vel_spin.setValue(self.frame_data.get_velocity_scale(joint_name))
            self.enable_checkbox_widgets[joint_name].setChecked(self.frame_data.get_enable(joint_name))

    def accept(self):
        self.frame_data.move_duration = self.move_spin.value()
        self.frame_data.wait_duration = self.wait_spin.value()

        for joint_name in self.joint_data_manager.get_joint_names():
            _, spin, vel_spin = self.joint_widgets[joint_name]
            self.frame_data.set_pose(joint_name, math.radians(spin.value()))
            self.frame_data.set_velocity_scale(joint_name, vel_spin.value())
            self.frame_data.set_enable(joint_name, self.enable_checkbox_widgets[joint_name].isChecked())

        self.frame_data.save_to_file(self.filepath)
        super().accept()

    def set_prev_frame_data(self, frame_data: FrameData):
        self.prev_frame_data = frame_data

    def set_next_frame_data(self, frame_data: FrameData):
        self.next_frame_data = frame_data

    def _get_prev_frame_data(self):
        if self.prev_frame_data:
            return self.prev_frame_data
        return self._get_initial_frame_data()

    def _get_next_frame_data(self):
        if self.next_frame_data:
            return self.next_frame_data
        return self._get_initial_frame_data()

    def _get_initial_frame_data(self):
        try:
            path = self.motion_directory_manager.resolve_initial_frame_path()
            if os.path.exists(path):
                data = FrameData()
                data.set_joint_names(self.joint_data_manager.get_joint_names())
                data.load_from_file(path)
                return data
        except Exception as e:
            rospy.logwarn(f"[FrameEditorDialog] Failed to load initial_frame: {e}")

        try:
            path = self.motion_directory_manager.resolve_initial_pose_path()
            if os.path.exists(path):
                pose_data = InitialPoseData()
                pose_data.set_joint_names(self.joint_data_manager.get_joint_names())
                pose_data.load_from_file(path)
                frame = FrameData()
                frame.set_joint_names(self.joint_data_manager.get_joint_names())
                frame.set_joint_state(pose_data.get_joint_state())
                frame.move_duration = 1.0
                frame.wait_duration = 0.0
                return frame
        except Exception as e:
            rospy.logwarn(f"[FrameEditorDialog] Failed to load initial_pose: {e}")

        frame = FrameData()
        joint_names = self.joint_data_manager.get_joint_names()
        frame.set_joint_names(joint_names)
        frame.set_joint_state(JointState(name=joint_names, position=[0.0] * len(joint_names)))
        frame.move_duration = 1.0
        frame.wait_duration = 0.0
        return frame
