import importlib.resources
import warnings
from typing import Self

from PySide6 import QtWidgets, QtHelp

from ..._common.help_widget import HelpWidget


class HelpDialog(QtWidgets.QDialog):
    def __init__(self, help_engine, parent=None):
        super().__init__(parent)

        self.help_widget = HelpWidget(help_engine)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.help_widget)
        self.setLayout(layout)

    @classmethod
    def new(cls, parent=None) -> Self:
        help_file = importlib.resources.files("caqtus.gui.condetrol._help").joinpath(
            "Condetrol.qhc"
        )
        if not help_file.is_file():
            # We just raise a warning here, because if the help file is not found, the
            # help engine will create an empty help file, but will not raise an error.
            warnings.warn("Help file not found, help dialog will be empty.")
        help_engine = QtHelp.QHelpEngine(str(help_file))
        dialog = cls(help_engine, parent)
        if not help_engine.setupData():
            raise RuntimeError("Failed to set up help engine.")
        help_engine.setReadOnly(True)
        return dialog
