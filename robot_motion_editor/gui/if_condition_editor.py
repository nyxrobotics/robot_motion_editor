from PyQt5.QtWidgets import QComboBox
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtWidgets import QVBoxLayout


class IfConditionExpressionDialog(QDialog):
    def __init__(self, available_variables, frame_names, existing_names=None,
                 name="", condition="", to_true="", to_false="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("If Condition Editor")
        self.result = None
        self.available_variables = available_variables or []
        self.existing_names = set(existing_names or [])

        self.init_ui(name, condition, frame_names, to_true, to_false)

    def init_ui(self, name, current_expr, frame_names, to_true, to_false):
        layout = QVBoxLayout()

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Condition Name:"))
        self.name_edit = QLineEdit(name)
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        layout.addWidget(QLabel("Enter if condition (e.g., imu_pitch > 0.1):"))

        self.expr_edit = QTextEdit()
        self.expr_edit.setPlainText(current_expr)
        layout.addWidget(self.expr_edit)

        # to_true
        true_layout = QHBoxLayout()
        true_layout.addWidget(QLabel("If True →"))
        self.true_combo = QComboBox()
        self.true_combo.addItems(frame_names)
        self.true_combo.setCurrentText(to_true)
        true_layout.addWidget(self.true_combo)
        layout.addLayout(true_layout)

        # to_false
        false_layout = QHBoxLayout()
        false_layout.addWidget(QLabel("If False →"))
        self.false_combo = QComboBox()
        self.false_combo.addItems(frame_names)
        self.false_combo.setCurrentText(to_false)
        false_layout.addWidget(self.false_combo)
        layout.addLayout(false_layout)

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
        name = self.name_edit.text().strip()
        expr = self.expr_edit.toPlainText().strip()

        if not name:
            QMessageBox.warning(self, "Missing Name", "Please provide a unique condition name.")
            return

        if name in self.existing_names:
            QMessageBox.warning(self, "Name Conflict", f"'{name}' already exists. Choose another name.")
            return

        if not self.validate_expression(expr):
            QMessageBox.critical(
                self, "Invalid Expression",
                "The expression contains syntax errors or undefined variables."
            )
            return

        self.result = {
            "name": name,
            "condition": expr,
            "to_true": self.true_combo.currentText(),
            "to_false": self.false_combo.currentText()
        }
        self.accept()
