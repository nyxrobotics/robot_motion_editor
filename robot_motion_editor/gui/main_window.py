import glob

from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QTabWidget
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QWidget

from robot_motion_editor.gui.initial_pose_editor import InitialPoseEditor
from robot_motion_editor.robot_interface.urdf_joint_extractor import get_transmission_joints


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robot Motion Editor")
        self.resize(1000, 800)

        self.joint_names = get_transmission_joints()
        self.variable_names = self.generate_variable_names()
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

    def init_ui(self):
        layout = QVBoxLayout()

        self.torque_checkbox = QCheckBox("Torque ON")
        self.init_pose_button = QPushButton("Move to Initial Pose")
        self.save_all_button = QPushButton("Save All")
        self.hardware_checkbox = QCheckBox("Use Real Robot")

        com_layout = QHBoxLayout()
        self.com_port_box = QComboBox()
        self.refresh_ports_button = QPushButton("Refresh Ports")
        self.refresh_ports_button.clicked.connect(self.update_serial_ports)
        self.update_serial_ports()
        com_layout.addWidget(QLabel("COM Port:"))
        com_layout.addWidget(self.com_port_box)
        com_layout.addWidget(self.refresh_ports_button)

        self.baudrate_combo = QComboBox()
        baud_rates = ["4500000", "4000000", "3000000", "2000000", "1000000", "115200", "57600", "9600"]
        self.baudrate_combo.addItems(baud_rates)
        self.baudrate_combo.setEditable(True)
        self.baudrate_combo.setCurrentText("115200")

        layout.addWidget(self.torque_checkbox)
        layout.addWidget(self.init_pose_button)
        layout.addWidget(self.save_all_button)
        layout.addLayout(com_layout)
        layout.addWidget(QLabel("Baudrate:"))
        layout.addWidget(self.baudrate_combo)
        layout.addWidget(self.hardware_checkbox)

        self.tabs = QTabWidget()
        self.tabs.addTab(InitialPoseEditor(self.joint_names), "Initial Pose")
        layout.addWidget(self.tabs)

        self.setLayout(layout)
