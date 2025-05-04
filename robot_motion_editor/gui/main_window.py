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

from robot_motion_editor.gui.initial_pose_editor import InitialPoseEditor
from robot_motion_editor.gui.motion_editor import MotionEditorWidget
from robot_motion_editor.robot_interface.urdf_joint_extractor import get_joint_limit
from robot_motion_editor.robot_interface.urdf_joint_extractor import get_transmission_joints
from robot_motion_editor.visualizer.trajectory_visualizer import TrajectoryVisualizer


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robot Motion Editor")
        self.resize(1000, 800)

        self.joint_names = get_transmission_joints()
        self.joint_limits = {
            name: get_joint_limit(name)
            for name in self.joint_names
        }
        self.variable_names = self.generate_variable_names()

        # Initialize the trajectory visualizer
        self.trajectory_visualizer = TrajectoryVisualizer(visualize_as_state=True, rate=30.0)
        self.init_ui()

    def generate_variable_names(self):
        imu_vars = [
            "imu_roll", "imu_pitch", "imu_yaw",
            "imu_ang_vel_x", "imu_ang_vel_y", "imu_ang_vel_z",
            "imu_lin_acc_x", "imu_lin_acc_y", "imu_lin_acc_z"
        ]
        joint_vars = [f"joint_{name}" for name in self.joint_names]
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
            if self.initial_pose_editor:
                self.initial_pose_editor.set_motion_directory(folder)

    def init_ui(self):
        layout = QVBoxLayout()

        self.torque_checkbox = QCheckBox("Torque ON")
        self.init_pose_button = QPushButton("Move to Initial Pose")
        self.save_all_button = QPushButton("Save All")
        self.hardware_checkbox = QCheckBox("Use Real Robot")

        self.variable_names = self.generate_variable_names()

        checkbox_row = QHBoxLayout()
        checkbox_row.addWidget(self.torque_checkbox)
        checkbox_row.addStretch()
        checkbox_row.addWidget(self.hardware_checkbox)

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
        layout.addWidget(self.save_all_button)
        layout.addLayout(com_layout)
        layout.addLayout(baud_layout)
        layout.addLayout(path_layout)

        self.tabs = QTabWidget()
        self.initial_pose_editor = InitialPoseEditor(
            self.joint_names,
            self.joint_limits,
            available_variables=self.variable_names,
            motion_directory="motion_directory",
            trajectory_visualizer=self.trajectory_visualizer)
        self.tabs.addTab(self.initial_pose_editor, "Initial Pose")

        self.motion_editor = MotionEditorWidget(
            motion_directory="motion_directory",
            joint_names=self.joint_names,
            joint_limits=self.joint_limits,
            available_variables=self.variable_names
        )
        self.tabs.addTab(self.motion_editor, "Motion Editor")

        layout.addWidget(self.tabs)
        self.setLayout(layout)
