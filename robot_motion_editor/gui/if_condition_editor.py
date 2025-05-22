import os

from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtWidgets import QVBoxLayout

from ..logic.if_condition_file_manager import IfConditionData
from ..logic.if_condition_file_manager import IfConditionFileManager


class IfConditionEditorDialog(QDialog):
    def __init__(self, condition_path, available_variables=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"If Condition Editor: {os.path.basename(condition_path)}")
        self.available_variables = available_variables or []
        self.condition_path = condition_path
        self.motion_directory, self.animation_name, self.condition_name = self.parse_path(condition_path)
        self.init_ui()
        self.load_condition()

    def parse_path(self, path):
        condition_name = os.path.splitext(os.path.basename(path))[0]
        conditions_dir = os.path.dirname(os.path.dirname(path))
        animation_name = os.path.basename(os.path.dirname(conditions_dir))
        motion_directory = os.path.dirname(os.path.dirname(conditions_dir))
        return motion_directory, animation_name, condition_name

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
        QMessageBox.information(self, "Available Variables", "\n".join(self.available_variables))

    def load_condition(self):
        data_dict = IfConditionFileManager.load_dict(self.motion_directory, f"{self.condition_name}.yaml")
        if data_dict:
            cond_data = IfConditionData()
            cond_data.set_dict(data_dict)
            self.expression_edit.setPlainText(cond_data.expression)
            self.condition_edit.setPlainText(cond_data.condition)

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

        cond_data = IfConditionData(expression=expression, condition=condition)
        IfConditionFileManager.save_dict(
            os.path.join(self.motion_directory, self.animation_name, "conditions", "if"),
            cond_data.get_dict(),
            f"{self.condition_name}.yaml"
        )

        self.accept()
