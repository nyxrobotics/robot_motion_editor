import math
import os

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


class FrameEditorDialog(QDialog):
    def __init__(self, joint_names, joint_limits, available_variables, frame_path=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Frame")

        self.joint_names = joint_names
        self.joint_limits = joint_limits
        self.available_variables = available_variables
        self.frame_path = frame_path

        self.joint_widgets = {}
        self.joint_enabled = {}
        self.enable_checkbox_widgets = {}
        self.pid_config = {}
        self.feedback_expressions = {}
        self.velocity_scale = {}
        self.duration_value = 2.0
        self.wait_value = 0.0

        self.init_ui()

        if frame_path and os.path.exists(frame_path):
            self.load_frame_from_file(frame_path)

    def init_ui(self):
        layout = QVBoxLayout()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)

        # All Enable 行
        header_row = QHBoxLayout()
        self.all_enable_checkbox = QCheckBox("All Enable")
        self.all_enable_checkbox.stateChanged.connect(self.set_all_enable_checkboxes)
        header_row.addWidget(self.all_enable_checkbox)

        self.reset_all_button = QPushButton("Reset All")
        self.reset_all_button.clicked.connect(self.reset_all_positions)
        header_row.addWidget(self.reset_all_button)

        form.addRow(header_row)

        # 時間設定
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setDecimals(2)
        self.duration_spin.setRange(0.0, 10.0)
        self.duration_spin.setSingleStep(0.1)
        self.duration_spin.setValue(self.duration_value)

        self.wait_spin = QDoubleSpinBox()
        self.wait_spin.setDecimals(2)
        self.wait_spin.setRange(0.0, 10.0)
        self.wait_spin.setSingleStep(0.1)
        self.wait_spin.setValue(self.wait_value)

        form.addRow("Move Duration (sec)", self.duration_spin)
        form.addRow("Wait Time (sec)", self.wait_spin)

        # 最大ラベル幅を計算
        max_label_width = 0
        for joint in self.joint_names:
            label = QLabel(joint)
            max_label_width = max(max_label_width, label.sizeHint().width())

        # 各関節用
        for joint in self.joint_names:
            row = QHBoxLayout()

            enable_cb = QCheckBox()
            enable_cb.setChecked(True)
            self.joint_enabled[joint] = True
            enable_cb.stateChanged.connect(lambda state, j=joint: self.update_enable(j, state))
            self.enable_checkbox_widgets[joint] = enable_cb

            label = QLabel(joint)
            label.setFixedWidth(max_label_width)

            lower_rad, upper_rad = self.joint_limits.get(joint, (-math.pi, math.pi))
            lower_deg = math.degrees(lower_rad)
            upper_deg = math.degrees(upper_rad)

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

            vel_spin = QDoubleSpinBox()
            vel_spin.setDecimals(2)
            vel_spin.setSingleStep(0.1)
            vel_spin.setRange(0.0, 5.0)
            vel_spin.setValue(1.0)
            self.velocity_scale[joint] = 1.0
            vel_spin.valueChanged.connect(lambda val, j=joint: self.velocity_scale.update({j: val}))

            pid_btn = QPushButton("PID")
            pid_btn.setFixedWidth(50)
            fb_btn = QPushButton("FB")
            fb_btn.setFixedWidth(50)

            row.addWidget(enable_cb)
            row.addWidget(label)
            row.addWidget(slider)
            row.addWidget(spin)
            row.addWidget(QLabel("Vel"))
            row.addWidget(vel_spin)
            row.addWidget(pid_btn)
            row.addWidget(fb_btn)

            form.addRow(row)

            self.joint_widgets[joint] = (slider, spin, vel_spin)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_frame)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def update_enable(self, joint, state):
        self.joint_enabled[joint] = (state == Qt.Checked)

    def set_all_enable_checkboxes(self, state):
        checked = (state == Qt.Checked)
        for joint, checkbox in self.enable_checkbox_widgets.items():
            checkbox.blockSignals(True)
            checkbox.setChecked(checked)
            self.joint_enabled[joint] = checked
            checkbox.blockSignals(False)

    def reset_all_positions(self):
        for slider, spin, _ in self.joint_widgets.values():
            slider.blockSignals(True)
            spin.blockSignals(True)
            slider.setValue(0)
            spin.setValue(0.0)
            slider.blockSignals(False)
            spin.blockSignals(False)

    def load_frame_from_file(self, path):
        with open(path, "r") as f:
            data = yaml.safe_load(f)

        if not data:
            return

        time_data = data.get("time", {})
        self.duration_spin.setValue(time_data.get("duration", 2.0))
        self.wait_spin.setValue(time_data.get("wait", 0.0))

        velocity_data = data.get("velocity_scale", {})
        joints_data = data.get("joints", {})

        for name, settings in joints_data.items():
            if name not in self.joint_widgets:
                continue

            pos_rad = settings.get("position", 0.0)
            pos_deg = math.degrees(pos_rad)
            _, spin, vel_spin = self.joint_widgets[name]
            spin.setValue(pos_deg)

            enable = settings.get("enable", True)
            self.joint_enabled[name] = enable

            self.pid_config[name] = settings.get("pid", [0.0, 0.0, 0.0])
            self.feedback_expressions[name] = settings.get("feedback", "")

        for name, vscale in velocity_data.items():
            if name in self.joint_widgets:
                _, _, vel_spin = self.joint_widgets[name]
                vel_spin.setValue(vscale)

    def save_frame(self):
        if not self.frame_path:
            self.reject()
            return

        output = {
            "time": {
                "duration": self.duration_spin.value(),
                "wait": self.wait_spin.value(),
            },
            "velocity_scale": {name: self.joint_widgets[name][2].value() for name in self.joint_names},
            "joints": {}
        }

        for name in self.joint_names:
            _, spin, _ = self.joint_widgets[name]
            pos_deg = spin.value()
            pos_rad = math.radians(pos_deg)

            output["joints"][name] = {
                "position": pos_rad,
                "enable": self.joint_enabled.get(name, True),
                "pid": self.pid_config.get(name, [0.0, 0.0, 0.0]),
                "feedback": self.feedback_expressions.get(name, "")
            }

        with open(self.frame_path, "w") as f:
            yaml.safe_dump(output, f, allow_unicode=True)

        self.accept()
