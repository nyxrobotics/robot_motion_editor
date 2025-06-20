import copy
import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QListWidget
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtWidgets import QVBoxLayout

from ..logic.joint_data_manager import JointDataManager
from ..logic.motion_file_manager import MotionFileManager
from ..logic.switch_condition_file_manager import SwitchConditionData


class SwitchConditionEditorDialog(QDialog):
    def __init__(
            self,
            joint_data_manager: JointDataManager,
            motion_file_manager: MotionFileManager,
            filename: str, parent=None):
        super().__init__(parent)
        if parent is None:
            self.setWindowFlags(Qt.Window)
        self.joint_data_manager = joint_data_manager
        self.motion_file_manager = motion_file_manager
        self.filename = filename
        self.condition_data = SwitchConditionData()
        self.init_ui()
        self.load_condition()
        self.setWindowTitle(f"Switch: {self.motion_file_manager._resolve_switch_condition_path(self.filename)}")

    def init_ui(self):
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Expression:"))
        self.expression_edit = QTextEdit()
        layout.addWidget(self.expression_edit, stretch=3)

        layout.addWidget(QLabel("Condition (evaluates to int):"))
        self.condition_edit = QTextEdit()
        layout.addWidget(self.condition_edit, stretch=1)

        layout.addWidget(QLabel("Cases:"))
        self.case_list = QListWidget()
        self.case_list.setSelectionMode(QListWidget.NoSelection)
        layout.addWidget(self.case_list, stretch=2)

        case_btn_layout = QHBoxLayout()
        self.add_case_btn = QPushButton("＋")
        self.add_case_btn.clicked.connect(self.add_case)
        case_btn_layout.addWidget(self.add_case_btn)

        self.remove_case_btn = QPushButton("－")
        self.remove_case_btn.clicked.connect(self.remove_case)
        case_btn_layout.addWidget(self.remove_case_btn)

        layout.addLayout(case_btn_layout)

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
        self.condition_data = copy.deepcopy(self.motion_file_manager.get_switch(self.filename))
        self.expression_edit.setPlainText(self.condition_data.expression)
        self.condition_edit.setPlainText(self.condition_data.condition)

        self.case_list.clear()
        if isinstance(self.condition_data.case, dict):
            sorted_keys = sorted(self.condition_data.case.keys(), key=lambda k: int(k.split("_")[1]))
            for key in sorted_keys:
                self.case_list.addItem(key)

    def add_case(self):
        current_count = self.case_list.count()
        self.case_list.addItem(f"case_{current_count}")

    def remove_case(self):
        count = self.case_list.count()
        if count > 0:
            self.case_list.takeItem(count - 1)

    def accept_and_store(self):
        expression = self.expression_edit.toPlainText().strip()
        condition = self.condition_edit.toPlainText().strip()
        case_count = self.case_list.count()

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
                QMessageBox.critical(self, "Invalid Condition", f"Cannot evaluate condition.\n{str(e)}")
                return
            else:
                QMessageBox.critical(self, "Syntax Error in Condition", str(e))
                return

        if not isinstance(result, int):
            QMessageBox.warning(
                self,
                "Non-Integer Condition",
                f"The condition evaluates to a non-integer value: {result}\n"
                "This may not match any case."
            )

        case_dict = {f"case_{i}": {"value": i} for i in range(case_count)}

        self.condition_data.expression = expression
        self.condition_data.condition = condition
        self.condition_data.case = case_dict

        self.motion_file_manager.set_switch(self.filename, self.condition_data)

        self.result = {"num_cases": case_count + 1}
        self.accept()
