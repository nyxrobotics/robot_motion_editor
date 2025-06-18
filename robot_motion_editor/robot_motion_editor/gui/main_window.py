import glob
import os

from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QTabWidget
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget

from ..logic.joint_data_manager import JointDataManager
from ..logic.motion_file_manager import MotionFileManager
from ..robot_interface.trajectory_commander import TrajectoryCommander
from ..urdf_interface.urdf_joint_extractor import get_joint_limit
from ..urdf_interface.urdf_joint_extractor import get_robot_name
from ..urdf_interface.urdf_joint_extractor import get_transmission_joints
from ..visualizer.trajectory_visualizer import TrajectoryVisualizer
from .animation_widget import AnimaitonWidget
from .initial_pose_editor import InitialPoseEditor


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robot Motion Editor")
        self.resize(1000, 800)

        self.joint_data_manager = JointDataManager(
            joint_names=get_transmission_joints()
        )
        self.joint_data_manager.set_joint_limits({
            name: get_joint_limit(name) for name in self.joint_data_manager.get_joint_names()
        })
        self.joint_data_manager.set_available_variables(self.generate_variable_names())

        self.trajectory_visualizer = TrajectoryVisualizer(use_state_mode=True, playback_rate=30.0)
        self.trajectory_commander = TrajectoryCommander(
            get_robot_name(), self.joint_data_manager.get_joint_names(), mode="position")
        self.motion_file_manager = MotionFileManager(motion_directory=".")

        self.init_ui()

    def generate_variable_names(self):
        imu_vars = [
            "imu_roll", "imu_pitch", "imu_yaw",
            "imu_ang_vel_x", "imu_ang_vel_y", "imu_ang_vel_z",
            "imu_lin_acc_x", "imu_lin_acc_y", "imu_lin_acc_z"
        ]
        joint_vars = [f"joint_{name}" for name in self.joint_data_manager.get_joint_names()]
        return joint_vars + imu_vars

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Motion Directory", os.getcwd())
        if folder:
            self.path_lineedit.setText(folder)
            self.motion_file_manager.set_motion_directory(folder)
            self.motion_file_manager.clear()
            self.motion_file_manager.set_joint_names(self.joint_data_manager.get_joint_names())

            if self.initial_pose_editor:
                self.initial_pose_editor.load_pose()
            if self.animation_widget:
                self.animation_widget.reload_animation_tree()

    def init_ui(self):
        layout = QVBoxLayout()

        self.torque_checkbox = QCheckBox("Torque ON")
        self.torque_checkbox.setChecked(False)
        self.torque_checkbox.stateChanged.connect(
            lambda state: self.trajectory_commander.torque_on() if state else self.trajectory_commander.torque_off()
        )

        self.init_pose_button = QPushButton("Move to Initial Pose")

        self.preview_checkbox = QCheckBox("Preview")
        self.preview_checkbox.setChecked(True)
        self.preview_checkbox.stateChanged.connect(
            lambda state: self.trajectory_visualizer.enable() if state else self.trajectory_visualizer.disable()
        )

        self.hardware_checkbox = QCheckBox("Use Real Robot")
        self.hardware_checkbox.setChecked(False)
        self.hardware_checkbox.stateChanged.connect(
            lambda state: self.trajectory_commander.enable() if state else self.trajectory_commander.disable()
        )

        checkbox_row = QHBoxLayout()
        checkbox_row.addWidget(self.preview_checkbox)
        checkbox_row.addWidget(self.hardware_checkbox)
        checkbox_row.addWidget(self.torque_checkbox)

        path_layout = QHBoxLayout()
        self.path_lineedit = QLineEdit()
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_folder)
        path_layout.addWidget(QLabel("Motion Directory:"))
        path_layout.addWidget(self.path_lineedit)
        path_layout.addWidget(self.browse_button)

        layout.addLayout(checkbox_row)
        layout.addWidget(self.init_pose_button)
        layout.addLayout(path_layout)

        self.tabs = QTabWidget()
        self.initial_pose_editor = InitialPoseEditor(
            joint_data_manager=self.joint_data_manager,
            motion_file_manager=self.motion_file_manager,
            trajectory_visualizer=self.trajectory_visualizer,
            trajectory_commander=self.trajectory_commander
        )
        self.tabs.addTab(self.initial_pose_editor, "Initial Pose")

        self.animation_widget = AnimaitonWidget(
            motion_file_manager=self.motion_file_manager,
            item_file_manager=self.item_file_manager,
            joint_data_manager=self.joint_data_manager,
            trajectory_visualizer=self.trajectory_visualizer,
            trajectory_commander=self.trajectory_commander
        )
        self.tabs.addTab(self.animation_widget, "Motion Editor")

        layout.addWidget(self.tabs)
        self.setLayout(layout)
