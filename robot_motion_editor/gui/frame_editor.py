import math
import os

import yaml
from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QDialogButtonBox
from PyQt5.QtWidgets import QDoubleSpinBox
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QScrollArea
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget

from ..gui.feedback_expression_dialog import FeedbackExpressionDialog
from ..gui.pid_config_dialog import PIDConfigDialog


class FrameEditorDialog(QDialog):
    def __init__(self, joint_names, joint_limits, available_variables, frame_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Frame")
        self.joint_names = joint_names
        self.joint_limits = joint_limits
        self.available_variables = available_variables
        self.frame_path = frame_path

        self.joint_widgets = {}
        self.pid_config = {}
        self.feedback_expressions = {}

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # 時間指定
        time_row = QHBoxLayout()
        time_row.addWidget(QLabel("Duration (s):"))
        self.duration_input = QLineEdit("2.0")
        self.duration_input.setFixedWidth(60)
        time_row.addWidget(self.duration_input)

        time_row.addWidget(QLabel("Wait Time (s):"))
        self.wait_input = QLineEdit("1.0")
        self.wait_input.setFixedWidth(60)
        time_row.addWidget(self.wait_input)
        main_layout.addLayout(time_row)

        # スクロール領域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)

        if self.joint_names:
            max_label = QLabel(max(self.joint_names, key=len))
        else:
            max_label = QLabel("Joint")
        max_label_width = max_label.sizeHint().width()

        for joint in self.joint_names:
            row = QHBoxLayout()

            enable_cb = QCheckBox()
            enable_cb.setChecked(True)

            label = QLabel(joint)
            label.setFixedWidth(max_label_width)

            spin = QDoubleSpinBox()
            spin.setDecimals(1)
            spin.setSingleStep(1.0)

            lower_rad, upper_rad = self.joint_limits.get(joint, (-math.pi, math.pi))
            lower_deg = math.degrees(lower_rad)
            upper_deg = math.degrees(upper_rad)

            spin.setRange(lower_deg, upper_deg)
            spin.setValue(0.0)

            pid_button = QPushButton("PID")
            pid_button.setFixedWidth(50)
            pid_button.clicked.connect(lambda _, j=joint, btn=pid_button: self.open_pid_dialog(j, btn))

            fb_button = QPushButton("FB")
            fb_button.setFixedWidth(50)
            fb_button.clicked.connect(lambda _, j=joint, btn=fb_button: self.open_feedback_dialog(j, btn))

            velocity_input = QLineEdit("1.0")
            velocity_input.setFixedWidth(50)

            row.addWidget(enable_cb)
            row.addWidget(label)
            row.addWidget(spin)
            row.addWidget(QLabel("×"))
            row.addWidget(velocity_input)
            row.addWidget(pid_button)
            row.addWidget(fb_button)
            layout.addLayout(row)

            self.joint_widgets[joint] = {
                "enable": enable_cb,
                "spin": spin,
                "velocity": velocity_input,
                "pid": [0.0, 0.0, 0.0],
                "feedback": ""
            }

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        # OK/Cancel
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_and_accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

        self.setLayout(main_layout)

    def open_pid_dialog(self, joint_name, button):
        current = self.joint_widgets[joint_name].get("pid", [0.0, 0.0, 0.0])
        dialog = PIDConfigDialog(joint_name, current, parent=self)
        if dialog.exec_() and dialog.result:
            self.joint_widgets[joint_name]["pid"] = dialog.result
            p, i, d = dialog.result
            if any(val != 0.0 for val in (p, i, d)):
                button.setStyleSheet("background-color: lightblue;")
            else:
                button.setStyleSheet("")

    def open_feedback_dialog(self, joint_name, button):
        current_expr = self.joint_widgets[joint_name].get("feedback", "")
        dialog = FeedbackExpressionDialog(
            joint_name, current_expr, self.available_variables, parent=self
        )
        if dialog.exec_() and dialog.result is not None:
            self.joint_widgets[joint_name]["feedback"] = dialog.result
            expr = dialog.result.strip()
            button.setStyleSheet("background-color: lightblue" if expr else "")

    def get_frame_data(self):
        data = {
            "time": {
                "duration": float(self.duration_input.text()),
                "wait": float(self.wait_input.text())
            },
            "joints": {},
            "velocity_scale": {}
        }
        for name, widgets in self.joint_widgets.items():
            pos_deg = widgets["spin"].value()
            pos_rad = math.radians(pos_deg)
            data["joints"][name] = {
                "position": pos_rad,
                "enable": widgets["enable"].isChecked(),
                "pid": widgets["pid"],
                "feedback": widgets["feedback"]
            }
            data["velocity_scale"][name] = float(widgets["velocity"].text())
        return data

    def save_and_accept(self):
        try:
            frame_data = self.get_frame_data()
            os.makedirs(os.path.dirname(self.frame_path), exist_ok=True)
            with open(self.frame_path, "w") as f:
                yaml.safe_dump(frame_data, f, default_flow_style=False)
            print(f"[INFO] Frame saved to {self.frame_path}")
        except Exception as e:
            print(f"[ERROR] Failed to save frame: {e}")
        self.accept()
