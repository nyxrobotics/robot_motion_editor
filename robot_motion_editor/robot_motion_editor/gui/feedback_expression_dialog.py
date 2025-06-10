from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtWidgets import QVBoxLayout


class FeedbackExpressionDialog(QDialog):
    def __init__(self, joint_name, current_expr="", available_variables=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{joint_name} Feedback Expression")
        self.joint_name = joint_name
        self.available_variables = available_variables or []
        self.result = None

        self.init_ui(current_expr)

    def init_ui(self, current_expr):
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Enter feedback expression (e.g., 0.5 * imu_pitch + joint_knee):"))

        self.expr_edit = QTextEdit()
        self.expr_edit.setPlainText(current_expr)
        layout.addWidget(self.expr_edit)

        btn_layout = QHBoxLayout()

        show_vars_btn = QPushButton("Show Variables")
        show_vars_btn.clicked.connect(self.show_variables)

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept_and_store)

        btn_layout.addWidget(show_vars_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def show_variables(self):
        text = "\n".join(self.available_variables)
        QMessageBox.information(self, "Available Variables", text)

    def validate_expression(self, expr):
        if not expr.strip():
            return True
        try:
            code = compile(expr, "<string>", "eval")
        except SyntaxError:
            return False
        for name in code.co_names:
            if name not in self.available_variables:
                return False
        return True

    def accept_and_store(self):
        expr = self.expr_edit.toPlainText().strip()
        if not self.validate_expression(expr):
            QMessageBox.critical(
                self, "Invalid Expression",
                "The expression contains syntax errors or undefined variables."
            )
            return
        self.result = expr
        self.accept()
