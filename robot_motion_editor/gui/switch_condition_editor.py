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
        layout.addWidget(self.condition_edit, stretch=1)  # expressionの1/3の高さ

        layout.addWidget(QLabel("Cases:"))
        self.case_list = QListWidget()
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
        QMessageBox.information(self, "Available Variables", "\n".join(self.available_variables))

    def load_condition(self):
        data = load_switch_condition(self.animation_root, self.animation_name, self.condition_name)
        if data:
            self.expression_edit.setPlainText(data.get('expression', ''))
            self.condition_edit.setPlainText(data.get('condition', ''))
            self.case_list.clear()
            for case in data.get('case', []):
                self.case_list.addItem(str(case))

    def add_case(self):
        new_case = 0
        if self.case_list.count() > 0:
            new_case = int(self.case_list.item(self.case_list.count() - 1).text()) + 1
        self.case_list.addItem(str(new_case))

    def remove_case(self):
        current_row = self.case_list.currentRow()
        if current_row >= 0:
            self.case_list.takeItem(current_row)


    def accept_and_store(self):
        expression = self.expression_edit.toPlainText().strip()
        condition = self.condition_edit.toPlainText().strip()
        cases = [int(self.case_list.item(i).text()) for i in range(self.case_list.count())]

        if not expression or not condition:
            QMessageBox.warning(self, "Error", "Expression and condition cannot be empty.")
            return

        try:
            local_vars = {}
            exec(expression, {}, local_vars)
            condition_value = eval(condition, {}, local_vars)
            if not isinstance(condition_value, int):
                raise ValueError("Condition must evaluate to an integer.")
        except Exception as e:
            QMessageBox.critical(self, "Syntax Error", str(e))
            return

        save_switch_condition(
            self.animation_root,
            self.animation_name,
            self.condition_name,
            {"expression": expression, "condition": condition, "case": cases}
        )

        # case数をresultとして返す
        self.result = {"num_cases": len(cases) + 1}  # defaultを含める
        self.accept()
