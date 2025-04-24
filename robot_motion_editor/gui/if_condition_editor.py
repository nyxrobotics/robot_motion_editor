from PyQt5.QtWidgets import QComboBox
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QGridLayout
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtWidgets import QVBoxLayout


class IfConditionEditorDialog(QDialog):
    def __init__(self, frame_names, available_variables, condition="", to_true="", to_false="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit If Condition")
        self.resize(420, 260)

        self.available_variables = available_variables
        self.condition = condition
        self.to_true = to_true
        self.to_false = to_false

        self.init_ui(frame_names)

    def init_ui(self, frame_names):
        layout = QVBoxLayout()

        # Condition input
        cond_layout = QHBoxLayout()
        cond_layout.addWidget(QLabel("Condition:"))
        self.condition_input = QLineEdit(self.condition)
        cond_layout.addWidget(self.condition_input)
        layout.addLayout(cond_layout)

        # Target frames
        grid = QGridLayout()
        grid.addWidget(QLabel("If True →"), 0, 0)
        self.true_combo = QComboBox()
        self.true_combo.addItems(frame_names)
        self.true_combo.setCurrentText(self.to_true)
        grid.addWidget(self.true_combo, 0, 1)

        grid.addWidget(QLabel("If False →"), 1, 0)
        self.false_combo = QComboBox()
        self.false_combo.addItems(frame_names)
        self.false_combo.setCurrentText(self.to_false)
        grid.addWidget(self.false_combo, 1, 1)

        layout.addLayout(grid)

        # Variable reference
        var_button = QPushButton("Show Variables")
        var_button.clicked.connect(self.show_variable_list)
        layout.addWidget(var_button)

        # Buttons
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def show_variable_list(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Available Variables")
        dlg.resize(300, 250)
        vbox = QVBoxLayout()
        label = QLabel("\n".join(self.available_variables))
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        vbox.addWidget(label)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        vbox.addWidget(close_btn)
        dlg.setLayout(vbox)
        dlg.exec_()

    def get_result(self):
        return {
            "condition": self.condition_input.text().strip(),
            "to_true": self.true_combo.currentText(),
            "to_false": self.false_combo.currentText()
        }
