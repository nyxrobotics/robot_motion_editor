import math

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

from .feedback_expression_dialog import FeedbackExpressionDialog
from .pid_config_dialog import PIDConfigDialog


class FrameEditorDialog(QDialog):
    def __init__(self, joint_names, joint_limits, available_variables, frame_path=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Frame")

        self.joint_names = joint_names
        self.joint_limits = joint_limits
        self.available_variables = available_variables or {}
        self.frame_path = frame_path

        self.joint_widgets = {}
        self.joint_enabled = {}
        self.pid_config = {}
        self.feedback_expressions = {}
        self.velocity_scale = {}
        self.enable_checkbox_widgets = {}

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)

        # Time fields
        time_row = QHBoxLayout()
        time_row.addWidget(QLabel("Move Time (s):"))
        self.move_time_spin = QDoubleSpinBox()
        self.move_time_spin.setRange(0.0, 30.0)
        self.move_time_spin.setSingleStep(0.1)
        time_row.addWidget(self.move_time_spin)

        time_row.addWidget(QLabel("Wait Time (s):"))
        self.wait_time_spin = QDoubleSpinBox()
        self.wait_time_spin.setRange(0.0, 30.0)
        self.wait_time_spin.setSingleStep(0.1)
        time_row.addWidget(self.wait_time_spin)
        content_layout.addLayout(time_row)

        # All Enable + Reset
        top_row = QHBoxLayout()
        self.all_enable_checkbox = QCheckBox("All Enable")
        self.all_enable_checkbox.stateChanged.connect(self.set_all_enable)
        top_row.addWidget(self.all_enable_checkbox)

        self.reset_all_button = QPushButton("Reset All")
        self.reset_all_button.clicked.connect(self.reset_all_angles)
        top_row.addWidget(self.reset_all_button)
        content_layout.addLayout(top_row)

        # Widget rows
        max_label = QLabel(max(self.joint_names, key=len) if self.joint_names else "Joint")
        max_label_width = max_label.sizeHint().width()

        for joint in self.joint_names:
            row = QHBoxLayout()

            enable_cb = QCheckBox()
            enable_cb.setChecked(True)
            self.joint_enabled[joint] = True
            enable_cb.stateChanged.connect(
                lambda state, j=joint: self.joint_enabled.__setitem__(j, state == Qt.Checked))
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

            vel_spin = QDoubleSpinBox()
            vel_spin.setDecimals(2)
            vel_spin.setRange(0.0, 5.0)
            vel_spin.setValue(1.0)
            self.velocity_scale[joint] = vel_spin

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
            row.addWidget(QLabel("Vel"))
            row.addWidget(vel_spin)
            row.addWidget(pid_btn)
            row.addWidget(fb_btn)
            content_layout.addLayout(row)

            self.joint_widgets[joint] = (slider, spin)
            self.pid_config[joint] = [0.0, 0.0, 0.0]
            self.feedback_expressions[joint] = ""

        scroll.setWidget(content)
        layout.addWidget(scroll)

        # OK/Cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
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
        for _, spin in self.joint_widgets.values():
            spin.setValue(0.0)

    def get_frame_data(self):
        joints = {}
        for name in self.joint_names:
            _, spin = self.joint_widgets[name]
            pos = math.radians(spin.value())
            joints[name] = {
                "position": pos,
                "enable": self.joint_enabled.get(name, True),
                "pid": self.pid_config.get(name, [0.0, 0.0, 0.0]),
                "feedback": self.feedback_expressions.get(name, "")
            }

        vel_scale = {name: self.velocity_scale[name].value() for name in self.joint_names}

        return {
            "time": {
                "duration": self.move_time_spin.value(),
                "wait": self.wait_time_spin.value()
            },
            "joints": joints,
            "velocity_scale": vel_scale
        }

    def open_pid_dialog(self, joint_name, button):
        current = self.pid_config.get(joint_name, [0.0, 0.0, 0.0])
        dialog = PIDConfigDialog(joint_name, current, parent=self)
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

    def load_frame_data(self, path):
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)

            time_data = data.get("time", {})
            self.move_time_spin.setValue(float(time_data.get("duration", 0.0)))
            self.wait_time_spin.setValue(float(time_data.get("wait", 0.0)))

            joints = data.get("joints", {})
            for name, values in joints.items():
                if name not in self.joint_widgets:
                    continue
                _, spin = self.joint_widgets[name]
                spin.setValue(math.degrees(values.get("position", 0.0)))
                self.joint_enabled[name] = bool(values.get("enable", True))
                cb = self.enable_checkbox_widgets.get(name)
                if cb:
                    cb.setChecked(self.joint_enabled[name])
                self.pid_config[name] = values.get("pid", [0.0, 0.0, 0.0])
                self.feedback_expressions[name] = values.get("feedback", "")

            velocity_data = data.get("velocity_scale", {})
            for name, val in velocity_data.items():
                if name in self.velocity_scale:
                    self.velocity_scale[name].setValue(val)
        except Exception as e:
            print(f"[WARN] Failed to load frame from {path}: {e}")
