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
from .feedback_expression_dialog import FeedbackExpressionDialog
from .pid_gain_editor import PIDGainEditorDialog


class InitialFrameEditorDialog(QDialog):
    def __init__(self, joint_names, joint_limits, available_variables, initial_frame_path=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Initial Frame")

        self.joint_names = joint_names
        self.joint_limits = joint_limits
        self.available_variables = available_variables or {}
        self.initial_frame_path = initial_frame_path

        self.frame_data = FrameData()
        self.frame_data.set_joint_names(joint_names)

        self.joint_widgets = {}
        self.enable_checkbox_widgets = {}

        self.init_ui()
        self.load_pose_from_file(initial_frame_path)

    def init_ui(self):
        layout = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)

        self.all_enable_checkbox = QCheckBox("All Enable")
        self.all_enable_checkbox.stateChanged.connect(self.set_all_enable_checkboxes)
        form.addRow(self.all_enable_checkbox)

        max_label_width = max(QLabel(j).sizeHint().width() for j in self.joint_names) if self.joint_names else 100

        for joint in self.joint_names:
            row = QHBoxLayout()

            enable_cb = QCheckBox()
            enable_cb.setChecked(True)
            enable_cb.stateChanged.connect(lambda state, j=joint: self.frame_data.set_enable(j, state == Qt.Checked))
            self.enable_checkbox_widgets[joint] = enable_cb

            label = QLabel(joint)
            label.setFixedWidth(max_label_width)

            lower_rad, upper_rad = self.joint_limits.get(joint, (-math.pi, math.pi))
            lower_deg, upper_deg = math.degrees(lower_rad), math.degrees(upper_rad)

            slider = QSlider(Qt.Horizontal)
            slider.setRange(int(lower_deg), int(upper_deg))
            slider.setSingleStep(1)
            slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            spin = QDoubleSpinBox()
            spin.setDecimals(1)
            spin.setSingleStep(1.0)
            spin.setRange(lower_deg, upper_deg)

            slider.valueChanged.connect(lambda val, s=spin: s.setValue(float(val)))
            spin.valueChanged.connect(lambda val, sl=slider: sl.setValue(int(round(val))))

            pid_btn = QPushButton("PID")
            pid_btn.setFixedWidth(50)
            pid_btn.clicked.connect(lambda _, j=joint, b=pid_btn: self.open_pid_dialog(j, b))

            fb_btn = QPushButton("FB")
            fb_btn.setFixedWidth(50)
            fb_btn.clicked.connect(lambda _, j=joint, b=fb_btn: self.open_feedback_dialog(j, b))

            row.addWidget(enable_cb)
            row.addWidget(label)
            row.addWidget(slider)
            row.addWidget(spin)
            row.addWidget(pid_btn)
            row.addWidget(fb_btn)

            form.addRow(row)
            self.joint_widgets[joint] = (slider, spin)
            self.frame_data.set_pid(joint, [0.0, 0.0, 0.0])
            self.frame_data.set_feedback(joint, "")

        scroll.setWidget(content)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_pose)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def set_all_enable_checkboxes(self, state):
        checked = (state == Qt.Checked)
        for name, cb in self.enable_checkbox_widgets.items():
            cb.blockSignals(True)
            cb.setChecked(checked)
            self.frame_data.set_enable(name, checked)
            cb.blockSignals(False)

    def load_pose_from_file(self, yaml_path):
        if not yaml_path or not os.path.exists(yaml_path):
            rospy.loginfo(f"No initial_frame.yaml found at {yaml_path}")
            return
        try:
            loaded = FrameFileManager.load_dict(os.path.dirname(yaml_path), os.path.basename(yaml_path))
            self.frame_data.set_dict(loaded)
            for joint in self.joint_names:
                _, spin = self.joint_widgets[joint]
                spin.setValue(math.degrees(self.frame_data.get_pose(joint)))
                self.enable_checkbox_widgets[joint].setChecked(self.frame_data.get_enable(joint))
        except Exception as e:
            rospy.logwarn(f"Failed to load initial_frame data: {e}")

    def save_pose(self):
        if self.initial_frame_path:
            for name in self.joint_names:
                _, spin = self.joint_widgets[name]
                self.frame_data.set_pose(name, math.radians(spin.value()))
            FrameFileManager.save_dict(
                os.path.dirname(self.initial_frame_path),
                self.frame_data.get_dict(),
                filename=os.path.basename(self.initial_frame_path))
            rospy.loginfo(f"Initial frame saved to {self.initial_frame_path}")
        self.accept()

    def open_pid_dialog(self, joint_name, button):
        current = self.frame_data.get_pid(joint_name)
        dialog = PIDGainEditorDialog(joint_name, current, parent=self)
        if dialog.exec_() and dialog.result:
            self.frame_data.set_pid(joint_name, dialog.result)
            button.setStyleSheet("background-color: lightblue;" if any(dialog.result) else "")

    def open_feedback_dialog(self, joint_name, button):
        current = self.frame_data.get_feedback(joint_name)
        dialog = FeedbackExpressionDialog(joint_name, current, self.available_variables, parent=self)
        if dialog.exec_() and dialog.result is not None:
            self.frame_data.set_feedback(joint_name, dialog.result)
            button.setStyleSheet("background-color: lightblue;" if dialog.result.strip() else "")

    def get_joint_data(self):
        return self.frame_data.get_dict()
