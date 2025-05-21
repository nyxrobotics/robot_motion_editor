import math
import os

import rospy
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QDialogButtonBox
from PyQt5.QtWidgets import QDoubleSpinBox
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QScrollArea
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtWidgets import QSlider
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget

from ..logic.initial_pose_file_manager import InitialPoseFileManager
from .feedback_expression_dialog import FeedbackExpressionDialog
from .pid_gain_editor import PIDGainEditorDialog


class OffsetEditorDialog(QDialog):
    def __init__(self, joint_names, joint_limits, available_variables, offset_path=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Initial Offset")

        self.joint_names = joint_names
        self.joint_limits = joint_limits
        self.available_variables = available_variables or {}
        self.offset_path = offset_path

        self.joint_widgets = {}
        self.joint_enabled = {}
        self.pid_config = {}
        self.feedback_expressions = {}
        self.enable_checkbox_widgets = {}

        self.init_ui()
        self.load_pose_from_file(offset_path)

    def init_ui(self):
        layout = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)

        top_row = QHBoxLayout()
        self.all_enable_checkbox = QCheckBox("All Enable")
        self.all_enable_checkbox.stateChanged.connect(self.set_all_enable)
        top_row.addWidget(self.all_enable_checkbox)

        self.reset_all_button = QPushButton("Reset All")
        self.reset_all_button.clicked.connect(self.reset_all_angles)
        top_row.addWidget(self.reset_all_button)

        content_layout.addLayout(top_row)

        if self.joint_names:
            max_label = QLabel(max(self.joint_names, key=len))
        else:
            max_label = QLabel("Joint")
            rospy.logwarn("No joints available.")
        max_label_width = max_label.sizeHint().width()

        for joint in self.joint_names:
            row = QHBoxLayout()

            enable_cb = QCheckBox()
            enable_cb.setChecked(True)
            self.joint_enabled[joint] = True
            enable_cb.stateChanged.connect(
                lambda state, j=joint: self.joint_enabled.__setitem__(
                    j, state == Qt.Checked))
            self.enable_checkbox_widgets[joint] = enable_cb

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
            content_layout.addLayout(row)

            self.joint_widgets[joint] = (slider, spin)
            self.pid_config[joint] = [0.0, 0.0, 0.0]
            self.feedback_expressions[joint] = ""

        scroll.setWidget(content)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def set_all_enable(self, state):
        checked = (state == Qt.Checked)
        for joint, cb in self.enable_checkbox_widgets.items():
            cb.blockSignals(True)
            cb.setChecked(checked)
            self.joint_enabled[joint] = checked
            cb.blockSignals(False)

    def reset_all_angles(self):
        for name, (slider, spin) in self.joint_widgets.items():
            spin.setValue(0.0)

    def load_pose_from_file(self, yaml_path):
        if not yaml_path or not os.path.exists(yaml_path):
            rospy.loginfo(f"No offset.yaml found at {yaml_path}")
            return

        try:
            loaded = InitialPoseFileManager.load_dict(os.path.dirname(yaml_path), os.path.basename(yaml_path))
            for name in self.joint_names:
                if name not in loaded:
                    continue
                data = loaded[name]
                _, spin = self.joint_widgets[name]
                spin.setValue(math.degrees(data.get("position", 0.0)))
                self.joint_enabled[name] = data.get("enable", True)
                if name in self.enable_checkbox_widgets:
                    self.enable_checkbox_widgets[name].setChecked(self.joint_enabled[name])
                self.pid_config[name] = data.get("pid", [0.0, 0.0, 0.0])
                self.feedback_expressions[name] = data.get("feedback", "")
        except Exception as e:
            rospy.logwarn(f"Failed to load offset data: {e}")

    def get_joint_data(self):
        result = {}
        for name in self.joint_names:
            _, spin = self.joint_widgets[name]
            pos = math.radians(spin.value())
            result[name] = {
                "position": pos,
                "enable": self.joint_enabled.get(name, True),
                "pid": self.pid_config.get(name, [0.0, 0.0, 0.0]),
                "feedback": self.feedback_expressions.get(name, "")
            }
        return result

    def on_accept(self):
        if self.offset_path:
            data = self.get_joint_data()
            InitialPoseFileManager.save_dict(
                os.path.dirname(self.offset_path),
                joint_names=list(data.keys()),
                positions=[v["position"] for v in data.values()],
                enabled={k: v["enable"] for k, v in data.items()},
                pid_config={k: v["pid"] for k, v in data.items()},
                feedback_exprs={k: v["feedback"] for k, v in data.items()},
                filename=os.path.basename(self.offset_path)
            )
            rospy.loginfo(f"Offset saved to {self.offset_path}")
        self.accept()

    def open_pid_dialog(self, joint_name, button):
        current = self.pid_config.get(joint_name, [0.0, 0.0, 0.0])
        dialog = PIDGainEditorDialog(joint_name, current, parent=self)
        if dialog.exec_() and dialog.result:
            self.pid_config[joint_name] = dialog.result
            if any(val != 0.0 for val in dialog.result):
                button.setStyleSheet("background-color: lightblue")
            else:
                button.setStyleSheet("")

    def open_feedback_dialog(self, joint_name, button):
        current = self.feedback_expressions.get(joint_name, "")
        dialog = FeedbackExpressionDialog(
            joint_name, current, self.available_variables, parent=self
        )
        if dialog.exec_() and dialog.result is not None:
            self.feedback_expressions[joint_name] = dialog.result
            expr = dialog.result.strip()
            button.setStyleSheet("background-color: lightblue" if expr else "")
