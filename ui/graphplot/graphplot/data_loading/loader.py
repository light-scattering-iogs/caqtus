from typing import Optional

from PySide6.QtWidgets import QWidget

from core.session import PureSequencePath
from .loader_ui import Ui_Loader


class DataLoader(QWidget, Ui_Loader):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setupUi(self)

        self.watchlist: set[PureSequencePath] = set()

    def add_sequence_to_watchlist(self, sequence_path: PureSequencePath):
        if sequence_path not in self.watchlist:
            self.watchlist.add(sequence_path)
            self.sequence_list.addItem(str(sequence_path))
