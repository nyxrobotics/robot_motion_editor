import rospy
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QListWidget
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtWidgets import QVBoxLayout


class SwitchConditionEditorDialog(QDialog):
    def __init__(self, available_variables=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Switch Condition")
        self.available_variables = available_variables or []
        self.result = None  # 保存する結果（dict）

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Expression input
        expr_row = QHBoxLayout()
        expr_row.addWidget(QLabel("Expression:"))
        self.expression_edit = QLineEdit()
        expr_row.addWidget(self.expression_edit)
        layout.addLayout(expr_row)

        # Condition input
        cond_row = QHBoxLayout()
        cond_row.addWidget(QLabel("Condition:"))
        self.condition_edit = QTextEdit()
        cond_row.addWidget(self.condition_edit)
        layout.addLayout(cond_row)

        # Case list
        case_label = QLabel("Cases (integers):")
        layout.addWidget(case_label)

        self.case_list = QListWidget()
        layout.addWidget(self.case_list)

        # Case management buttons
        case_btn_row = QHBoxLayout()
        self.add_case_btn = QPushButton("Add Case")
        self.add_case_btn.clicked.connect(self.add_case)
        self.remove_case_btn = QPushButton("Remove Case")
        self.remove_case_btn.clicked.connect(self.remove_case)
        case_btn_row.addWidget(self.add_case_btn)
        case_btn_row.addWidget(self.remove_case_btn)
        layout.addLayout(case_btn_row)

        # Action buttons
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
        """使用できる変数一覧をダイアログ表示"""
        text = "\n".join(self.available_variables)
        QMessageBox.information(self, "Available Variables", text)

    def validate_expression_and_condition(self, expression, condition):
        """expression を実行し、condition を整数に評価できるか確認"""
        local_vars = {}

        try:
            # expressionをexec実行（例: def button_id = 1）
            exec(expression, {}, local_vars)
        except Exception as e:
            rospy.logwarn(f"Expression error: {e}")
            return False

        try:
            # conditionを整数として評価
            value = eval(condition, {}, local_vars)
            if not isinstance(value, int):
                rospy.logwarn(f"Condition did not evaluate to int: {value}")
                return False
        except Exception as e:
            rospy.logwarn(f"Condition eval error: {e}")
            return False

        return True

    def add_case(self):
        """case番号を追加"""
        items = [int(self.case_list.item(i).text()) for i in range(self.case_list.count())]
        new_case = max(items) + 1 if items else 0
        self.case_list.addItem(str(new_case))

    def remove_case(self):
        """選択されたcaseを削除"""
        selected = self.case_list.currentRow()
        if selected >= 0:
            self.case_list.takeItem(selected)

    def accept_and_store(self):
        """OKボタン押下時のバリデーション＆保存"""
        expression = self.expression_edit.text().strip()
        condition = self.condition_edit.toPlainText().strip()
        cases = [int(self.case_list.item(i).text()) for i in range(self.case_list.count())]

        if not expression:
            QMessageBox.warning(self, "Missing Expression", "Please provide an expression.")
            return

        if not self.validate_expression_and_condition(expression, condition):
            QMessageBox.critical(
                self, "Invalid Expression or Condition",
                "The expression or condition could not be validated as a switch-case."
            )
            return

        self.result = {
            "expression": expression,
            "condition": condition,
            "case": cases
        }
        self.accept()

    def get_case_indices(self):
        """現在登録されているcase番号をリストで返す"""
        return [int(self.case_list.item(i).text()) for i in range(self.case_list.count())]
