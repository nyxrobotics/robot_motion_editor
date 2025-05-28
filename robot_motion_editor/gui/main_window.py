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
from ..logic.motion_directory_manager import MotionDirectoryManager
from ..robot_interface.trajectory_commander import TrajectoryCommander
from ..urdf_interface.urdf_joint_extractor import get_joint_limit
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

        self.trajectory_visualizer = TrajectoryVisualizer(visualize_as_state=True, rate=30.0)
        self.trajectory_commander = TrajectoryCommander(
            "kuroko", self.joint_data_manager.get_joint_names(), mode="position")
        self.motion_directory_manager = MotionDirectoryManager(motion_directory=".")

        self.init_ui()

    def generate_variable_names(self):
        imu_vars = [
            "imu_roll", "imu_pitch", "imu_yaw",
            "imu_ang_vel_x", "imu_ang_vel_y", "imu_ang_vel_z",
            "imu_lin_acc_x", "imu_lin_acc_y", "imu_lin_acc_z"
        ]
        joint_vars = [f"joint_{name}" for name in self.joint_data_manager.get_joint_names()]
        return joint_vars + imu_vars

    def get_available_serial_ports(self):
        ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
        return sorted(ports)

    def update_serial_ports(self):
        ports = self.get_available_serial_ports()
        self.com_port_box.clear()
        self.com_port_box.addItems(ports if ports else ["(no ports found)"])

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Motion Directory", os.getcwd())
        if folder:
            self.path_lineedit.setText(folder)
            self.motion_directory_manager.set_motion_directory(folder)

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
        checkbox_row.addStretch()
        checkbox_row.addWidget(self.torque_checkbox)

        com_layout = QHBoxLayout()
        self.com_port_box = QComboBox()
        self.refresh_ports_button = QPushButton("Refresh Ports")
        self.refresh_ports_button.clicked.connect(self.update_serial_ports)
        self.update_serial_ports()
        com_layout.addWidget(QLabel("COM Port:"))
        com_layout.addWidget(self.com_port_box)
        com_layout.addWidget(self.refresh_ports_button)

        baud_layout = QHBoxLayout()
        self.baudrate_combo = QComboBox()
        baud_rates = ["4500000", "4000000", "3000000", "2000000", "1000000", "115200", "57600", "9600"]
        self.baudrate_combo.addItems(baud_rates)
        self.baudrate_combo.setEditable(True)
        self.baudrate_combo.setCurrentText("115200")
        baud_layout.addWidget(QLabel("Baudrate:"))
        baud_layout.addWidget(self.baudrate_combo)

        path_layout = QHBoxLayout()
        self.path_lineedit = QLineEdit()
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_folder)
        path_layout.addWidget(QLabel("Motion Directory:"))
        path_layout.addWidget(self.path_lineedit)
        path_layout.addWidget(self.browse_button)

        layout.addLayout(checkbox_row)
        layout.addWidget(self.init_pose_button)
        layout.addLayout(com_layout)
        layout.addLayout(baud_layout)
        layout.addLayout(path_layout)

        self.tabs = QTabWidget()
        self.initial_pose_editor = InitialPoseEditor(
            joint_data_manager=self.joint_data_manager,
            motion_directory_manager=self.motion_directory_manager,
            trajectory_visualizer=self.trajectory_visualizer,
            trajectory_commander=self.trajectory_commander
        )
        self.tabs.addTab(self.initial_pose_editor, "Initial Pose")

        self.animation_widget = AnimaitonWidget(
            motion_directory_manager=self.motion_directory_manager,
            joint_data_manager=self.joint_data_manager,
            trajectory_visualizer=self.trajectory_visualizer,
            trajectory_commander=self.trajectory_commander
        )
        self.tabs.addTab(self.animation_widget, "Motion Editor")

        layout.addWidget(self.tabs)
        self.setLayout(layout)
