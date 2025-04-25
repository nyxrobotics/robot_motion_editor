import math
import os

import rospy
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QDialogButtonBox
from PyQt5.QtWidgets import QVBoxLayout

from ..logic.initial_pose_file_manager import load_initial_pose
from .initial_pose_editor import InitialPoseEditor


class OffsetEditorDialog(QDialog):
    def __init__(self, joints, offset_path=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Initial Offset")

        joint_names = list(joints.keys())
        joint_limits = {name: (-math.pi, math.pi) for name in joint_names}
        available_variables = {}

        self.editor = InitialPoseEditor(joint_names, joint_limits, available_variables)

        # offset.yaml が存在すれば読み込んで上書き（存在する関節名だけ）
        if offset_path and os.path.exists(offset_path):
            try:
                self.editor.load_joint_pose_from_file(
                    path=os.path.dirname(offset_path),
                    filename=os.path.basename(offset_path)
                )
                rospy.loginfo(f"Offset loaded from {offset_path}")
            except Exception as e:
                rospy.logwarn(f"Failed to load offset data: {e}")
        else:
            rospy.loginfo(f"No offset.yaml found at {offset_path}")

        # OK / Cancel ボタン
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(self.editor)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_joint_data(self):
        result = {}
        for name in self.editor.joint_names:
            _, spin = self.editor.joint_widgets[name]
            pos = math.radians(spin.value())
            result[name] = {
                "position": pos,
                "enable": self.editor.joint_enabled.get(name, True),
                "pid": self.editor.pid_config.get(name, [0.0, 0.0, 0.0]),
                "feedback": self.editor.feedback_expressions.get(name, "")
            }
        return result
