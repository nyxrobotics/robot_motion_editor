from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QDoubleSpinBox
from PyQt5.QtWidgets import QFormLayout
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QVBoxLayout


class PIDConfigDialog(QDialog):
    def __init__(self, joint_name, current_values=(0.0, 0.0, 0.0), parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{joint_name} PID Settings")
        self.joint_name = joint_name
        self.p, self.i, self.d = current_values
        self.result = None

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        form = QFormLayout()

        self.p_spin = QDoubleSpinBox()
        self.i_spin = QDoubleSpinBox()
        self.d_spin = QDoubleSpinBox()
        for spin in [self.p_spin, self.i_spin, self.d_spin]:
            spin.setDecimals(4)
            spin.setRange(0.0, 1000.0)

        self.p_spin.setValue(self.p)
        self.i_spin.setValue(self.i)
        self.d_spin.setValue(self.d)

        form.addRow("P:", self.p_spin)
        form.addRow("I:", self.i_spin)
        form.addRow("D:", self.d_spin)
        layout.addLayout(form)

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept_and_store)
        layout.addWidget(ok_button)

        self.setLayout(layout)

    def accept_and_store(self):
        self.result = (
            self.p_spin.value(),
            self.i_spin.value(),
            self.d_spin.value()
        )
        self.accept()
