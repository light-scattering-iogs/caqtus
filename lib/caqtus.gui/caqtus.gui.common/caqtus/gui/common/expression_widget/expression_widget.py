from PySide6.QtWidgets import QLineEdit


from caqtus.types.expression import Expression


class ExpressionWidget(QLineEdit):
    """A widget to enter an expression"""

    def set_expression(self, expression: Expression):
        self.setText(expression.body)

    def get_expression(self) -> Expression:
        return Expression(self.text())
