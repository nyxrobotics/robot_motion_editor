import os

from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QListWidget
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtWidgets import QVBoxLayout

from ..logic.switch_condition_file_manager import SwitchConditionData
from ..logic.switch_condition_file_manager import SwitchConditionFileManager


class SwitchConditionEditorDialog(QDialog):
    def __init__(self, condition_path, available_variables=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Switch Condition Editor: {os.path.basename(condition_path)}")
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
        data_dict = SwitchConditionFileManager.load_dict(
            os.path.join(self.motion_directory, self.animation_name, "conditions", "switch"),
            f"{self.condition_name}.yaml"
        )
        self.case_list.clear()

        if data_dict:
            cond_data = SwitchConditionData()
            cond_data.set_dict(data_dict)

            self.expression_edit.setPlainText(cond_data.expression)
            self.condition_edit.setPlainText(cond_data.condition)

            case_section = cond_data.case
            if isinstance(case_section, dict):
                sorted_keys = sorted(case_section.keys(), key=lambda k: int(k.split("_")[1]))
                for key in sorted_keys:
                    self.case_list.addItem(key)
            else:
                for i, val in enumerate(case_section):
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

        # 保存構造の生成
        case_dict = {}
        for i in range(case_count):
            case_dict[f"case_{i}"] = {"value": i}

        cond_data = SwitchConditionData(
            expression=expression,
            condition=condition,
            case=case_dict
        )

        SwitchConditionFileManager.save_dict(
            os.path.join(self.motion_directory, self.animation_name, "conditions", "switch"),
            cond_data.get_dict(),
            f"{self.condition_name}.yaml"
        )

        self.result = {"num_cases": case_count + 1}  # default 含む
        self.accept()
