import math
import os
import tempfile

import rospy
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QDialogButtonBox
from PyQt5.QtWidgets import QVBoxLayout

from ..logic.initial_pose_file_manager import load_initial_pose
from ..logic.initial_pose_file_manager import save_initial_pose
from .initial_pose_editor import InitialPoseEditor


class OffsetEditorDialog(QDialog):
    def __init__(self, joints, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Initial Offset")

        joint_names = list(joints.keys())
        joint_limits = {name: (-math.pi, math.pi) for name in joint_names}
        available_variables = {}

        self.editor = InitialPoseEditor(joint_names, joint_limits, available_variables)

        # Load existing values into the editor via temp directory
        tmpdir = tempfile.mkdtemp()
        self.editor.set_motion_directory(tmpdir)

        # Load offset data
        offset_data = {}
        if os.path.exists(os.path.join(tmpdir, "offset.yaml")):
            offset_data = load_initial_pose(tmpdir, "offset.yaml")
            rospy.loginfo(f"Loaded offset data: {offset_data}")
        else:
            rospy.loginfo("Offset data file not found: {tmpdir}/offset.yaml")

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
