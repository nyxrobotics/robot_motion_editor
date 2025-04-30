import os

from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QListWidget
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtWidgets import QVBoxLayout

from robot_motion_editor.logic.switch_condition_file_manager import load_switch_condition
from robot_motion_editor.logic.switch_condition_file_manager import save_switch_condition


class SwitchConditionEditorDialog(QDialog):
    def __init__(self, condition_path, available_variables=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Switch Condition Editor: {os.path.basename(condition_path)}")
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
        if not self.available_variables:
            QMessageBox.information(self, "Variables", "No available variables.")
        else:
            QMessageBox.information(self, "Available Variables", "\n".join(self.available_variables))

    def load_condition(self):
        data = load_switch_condition(self.animation_root, self.animation_name, self.condition_name)
        self.case_list.clear()
        self.expression_edit.setPlainText(data.get("expression", ""))
        self.condition_edit.setPlainText(data.get("condition", ""))
        case_values = data.get("case", [])
        case_values.sort()
        for i in range(len(case_values)):
            self.case_list.addItem(f"case_{i}")

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
        cases = list(range(case_count))  # 常に連番で保存

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

        save_switch_condition(
            self.animation_root,
            self.animation_name,
            self.condition_name,
            {"expression": expression, "condition": condition, "case": cases}
        )

        self.result = {"num_cases": case_count + 1}  # default含む
        self.accept()
