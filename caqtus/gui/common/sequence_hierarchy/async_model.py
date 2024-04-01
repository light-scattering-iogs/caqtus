from typing import Optional

from PySide6.QtCore import QObject, QAbstractItemModel, QModelIndex, Qt
from PySide6.QtGui import QStandardItemModel

from caqtus.session import ExperimentSessionMaker


class AsyncPathHierarchyModel(QAbstractItemModel):
    def __init__(
        self, session_maker: ExperimentSessionMaker, parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self.session_maker = session_maker

        self.tree = QStandardItemModel(self)

    def index(self, row, column, parent=QModelIndex()):
        return self.tree.index(row, column, parent)

    def parent(self, index=QModelIndex()):
        return self.tree.parent(index)

    def rowCount(self, parent=QModelIndex()):
        return self.tree.rowCount(parent)

    def columnCount(self, parent=QModelIndex()):
        return 1

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        item = self.tree.itemFromIndex(index)

        return None
