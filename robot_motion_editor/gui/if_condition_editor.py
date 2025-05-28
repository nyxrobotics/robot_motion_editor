import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtWidgets import QVBoxLayout

from ..logic.if_condition_file_manager import IfConditionData
from ..logic.joint_data_manager import JointDataManager
from ..logic.motion_directory_manager import MotionDirectoryManager


class IfConditionEditorDialog(QDialog):
    def __init__(
            self,
            joint_data_manager: JointDataManager,
            motion_directory_manager: MotionDirectoryManager,
            condition_name: str,
            parent=None):
        super().__init__(parent)
        if parent is None:
            self.setWindowFlags(Qt.Window)
        self.joint_data_manager = joint_data_manager
        self.motion_directory_manager = motion_directory_manager
        self.condition_name = condition_name
        self.condition_data = IfConditionData()
        self.init_ui()
        self.filepath = self.motion_directory_manager.resolve_if_condition_path(self.condition_name)
        if os.path.exists(self.filepath):
            self.load_condition()
        self.setWindowTitle(f"If: {os.path.basename(self.filepath)}")

    def init_ui(self):
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Expression:"))
        self.expression_edit = QTextEdit()
        layout.addWidget(self.expression_edit, stretch=3)

        layout.addWidget(QLabel("Condition:"))
        self.condition_edit = QTextEdit()
        layout.addWidget(self.condition_edit, stretch=1)

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
        QMessageBox.information(
            self, "Available Variables", "\n".join(
                self.joint_data_manager.get_available_variables()))

    def load_condition(self):
        file_path = self.motion_directory_manager.resolve_if_condition_path(self.condition_name)
        self.condition_data.load_from_file(file_path)
        self.expression_edit.setPlainText(self.condition_data.expression)
        self.condition_edit.setPlainText(self.condition_data.condition)

    def accept_and_store(self):
        expression = self.expression_edit.toPlainText().strip()
        condition = self.condition_edit.toPlainText().strip()

        if not condition:
            QMessageBox.warning(self, "Error", "Condition cannot be empty.")
            return

        local_vars = {}

        if expression:
            try:
                exec(expression, {}, local_vars)
            except Exception as e:
                QMessageBox.critical(self, "Syntax Error in Expression", str(e))
                return

        try:
            result = eval(condition, {}, local_vars)
        except Exception as e:
            if not expression:
                QMessageBox.critical(
                    self,
                    "Invalid Condition",
                    "Condition cannot be evaluated without Expression.\n"
                    f"Error: {str(e)}"
                )
                return
            else:
                QMessageBox.critical(self, "Syntax Error in Condition", str(e))
                return

        if not bool(result):
            QMessageBox.warning(
                self,
                "Condition Evaluates to False",
                f"The condition evaluates to a falsy value: {result}"
            )

        self.condition_data.expression = expression
        self.condition_data.condition = condition
        file_path = self.motion_directory_manager.resolve_if_condition_path(self.condition_name)
        self.condition_data.save_to_file(file_path)

        self.accept()
