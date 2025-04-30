import os

from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtWidgets import QVBoxLayout

from robot_motion_editor.logic.if_condition_file_manager import load_if_condition
from robot_motion_editor.logic.if_condition_file_manager import save_if_condition


class IfConditionEditorDialog(QDialog):
    def __init__(self, condition_path, available_variables=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"If Condition Editor: {os.path.basename(condition_path)}")
        self.available_variables = available_variables or []
        self.condition_path = condition_path
        self.animation_root, self.animation_name, self.condition_name = self.parse_path(condition_path)
        self.init_ui()
        self.load_condition()

    def parse_path(self, path):
        condition_name = os.path.splitext(os.path.basename(path))[0]
        conditions_dir = os.path.dirname(os.path.dirname(path))
        animation_name = os.path.basename(os.path.dirname(conditions_dir))
        animation_root = os.path.dirname(os.path.dirname(conditions_dir))
        return animation_root, animation_name, condition_name

    def init_ui(self):
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Expression:"))
        self.expression_edit = QTextEdit()
        layout.addWidget(self.expression_edit, stretch=3)

        layout.addWidget(QLabel("Condition:"))
        self.condition_edit = QTextEdit()
        layout.addWidget(self.condition_edit, stretch=1)  # expressionの1/3の高さ

        btn_row = QHBoxLayout()
        self.show_vars_btn = QPushButton("Show Variables")
        self.show_vars_btn.clicked.connect(self.show_variables)
        btn_row.addWidget(self.show_vars_btn)

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept_and_store)
        btn_row.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        layout.addLayout(btn_row)
        self.setLayout(layout)

    def show_variables(self):
        QMessageBox.information(self, "Available Variables", "\n".join(self.available_variables))

    def load_condition(self):
        data = load_if_condition(self.animation_root, self.animation_name, self.condition_name)
        if data:
            self.expression_edit.setPlainText(data.get('expression', ''))
            self.condition_edit.setPlainText(data.get('condition', ''))

    def accept_and_store(self):
        expression = self.expression_edit.toPlainText().strip()
        condition = self.condition_edit.toPlainText().strip()

        if not expression or not condition:
            QMessageBox.warning(self, "Error", "Expression and condition cannot be empty.")
            return

        try:
            local_vars = {}
            exec(expression, {}, local_vars)
            exec(f"if {condition}: pass", {}, local_vars)
        except Exception as e:
            QMessageBox.critical(self, "Syntax Error", str(e))
            return

        save_if_condition(
            self.animation_root,
            self.animation_name,
            self.condition_name,
            {"expression": expression, "condition": condition}
        )

        self.accept()
