import math
import os

import yaml
from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QDialogButtonBox
from PyQt5.QtWidgets import QDoubleSpinBox
from PyQt5.QtWidgets import QFormLayout
from PyQt5.QtWidgets import QGroupBox
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QScrollArea
from PyQt5.QtWidgets import QSpinBox
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget


class FrameEditorWidget(QWidget):
    def __init__(self, joint_names, joint_limits, available_variables):
        super().__init__()
        self.joint_names = joint_names
        self.joint_limits = joint_limits
        self.available_variables = available_variables

        self.joint_widgets = {}  # name -> dict of widgets
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Time section
        time_box = QGroupBox("Time Settings")
        time_layout = QFormLayout()
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.0, 10.0)
        self.duration_spin.setSingleStep(0.1)
        self.duration_spin.setValue(1.0)
        time_layout.addRow("Duration [s]", self.duration_spin)

        self.wait_spin = QDoubleSpinBox()
        self.wait_spin.setRange(0.0, 10.0)
        self.wait_spin.setSingleStep(0.1)
        self.wait_spin.setValue(0.0)
        time_layout.addRow("Wait Time [s]", self.wait_spin)

        time_box.setLayout(time_layout)
        layout.addWidget(time_box)

        # Joint section (scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        joint_layout = QVBoxLayout(scroll_content)

        for name in self.joint_names:
            row = QHBoxLayout()

            enable_cb = QCheckBox("Enable")
            enable_cb.setChecked(True)

            vel_spin = QDoubleSpinBox()
            vel_spin.setRange(0.0, 5.0)
            vel_spin.setSingleStep(0.1)
            vel_spin.setValue(1.0)

            pid_enable = QCheckBox("PID")
            p_spin = QDoubleSpinBox()
            i_spin = QDoubleSpinBox()
            d_spin = QDoubleSpinBox()
            for spin in (p_spin, i_spin, d_spin):
                spin.setRange(0.0, 1000.0)
                spin.setSingleStep(0.1)
                spin.setValue(0.0)
                spin.setEnabled(False)

            def toggle_pid(enabled):
                for spin in (p_spin, i_spin, d_spin):
                    spin.setEnabled(enabled)

            pid_enable.stateChanged.connect(lambda state, f=toggle_pid: f(state == 2))

            row.addWidget(QLabel(name))
            row.addWidget(enable_cb)
            row.addWidget(QLabel("Vel"))
            row.addWidget(vel_spin)
            row.addWidget(pid_enable)
            row.addWidget(QLabel("P"))
            row.addWidget(p_spin)
            row.addWidget(QLabel("I"))
            row.addWidget(i_spin)
            row.addWidget(QLabel("D"))
            row.addWidget(d_spin)

            joint_layout.addLayout(row)

            self.joint_widgets[name] = {
                "enable": enable_cb,
                "velocity": vel_spin,
                "pid_enable": pid_enable,
                "p": p_spin,
                "i": i_spin,
                "d": d_spin
            }

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

    def set_frame_data(self, data: dict):
        self.duration_spin.setValue(data.get("time", {}).get("duration", 1.0))
        self.wait_spin.setValue(data.get("time", {}).get("wait", 0.0))

        velocity_scale = data.get("velocity_scale", {})
        joints = data.get("joints", {})

        for name, widgets in self.joint_widgets.items():
            widgets["enable"].setChecked(joints.get(name, {}).get("enable", True))
            widgets["velocity"].setValue(velocity_scale.get(name, 1.0))

            pid = joints.get(name, {}).get("pid", [0.0, 0.0, 0.0])
            if isinstance(pid, list) and len(pid) == 3:
                if any(x != 0.0 for x in pid):
                    widgets["pid_enable"].setChecked(True)
                    widgets["p"].setValue(pid[0])
                    widgets["i"].setValue(pid[1])
                    widgets["d"].setValue(pid[2])
                else:
                    widgets["pid_enable"].setChecked(False)

    def get_frame_data(self):
        result = {
            "time": {
                "duration": self.duration_spin.value(),
                "wait": self.wait_spin.value()
            },
            "velocity_scale": {},
            "joints": {}
        }

        for name, widgets in self.joint_widgets.items():
            result["velocity_scale"][name] = widgets["velocity"].value()
            joint = {
                "enable": widgets["enable"].isChecked(),
                "pid": [0.0, 0.0, 0.0],
                "feedback": ""  # 未実装：将来対応
            }

            if widgets["pid_enable"].isChecked():
                joint["pid"] = [
                    widgets["p"].value(),
                    widgets["i"].value(),
                    widgets["d"].value()
                ]

            result["joints"][name] = joint

        return result


class FrameEditorDialog(QDialog):
    def __init__(self, joint_names, joint_limits, available_variables, frame_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Frame: {os.path.basename(frame_path)}")
        self.frame_path = frame_path

        self.editor = FrameEditorWidget(joint_names, joint_limits, available_variables)
        if os.path.exists(frame_path):
            with open(frame_path, "r") as f:
                data = yaml.safe_load(f)
            if data:
                self.editor.set_frame_data(data)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_and_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(self.editor)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def save_and_accept(self):
        data = self.editor.get_frame_data()
        with open(self.frame_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
        self.accept()
