import sys
import threading
from numbers import Real
from typing import Optional

from PyQt6.QtWidgets import QApplication

from variable.name import DottedVariableName
from .input_widget import UserInputDialog, RawVariableRange


class ExecUserInput:
    def __init__(
        self,
        title: str,
        variable_ranges: dict[DottedVariableName, RawVariableRange],
    ):
        self._lock = threading.Lock()
        self._widget: Optional[UserInputDialog] = None

        self._title = title
        self._variable_ranges = variable_ranges

    def run(self):
        app = QApplication(sys.argv)
        with self._lock:
            self._widget = UserInputDialog(self._title, self._variable_ranges)
        self._widget.show()
        app.exec()

    def get_current_values(self) -> dict[DottedVariableName, Real]:
        with self._lock:
            if self._widget is None:
                return {}
            return self._widget.get_current_values()
