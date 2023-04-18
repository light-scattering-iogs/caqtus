import sys

from PyQt6.QtWidgets import QApplication

from variable_name import VariableName
from .input_widget import UserInputDialog, EvaluatedVariableRange


def exec_user_input(title: str, variable_ranges: dict[VariableName, EvaluatedVariableRange]):
    app = QApplication(sys.argv)
    dialog = UserInputDialog(title, variable_ranges)
    dialog.show()
    app.exec()
