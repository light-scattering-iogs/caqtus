import functools
from typing import Optional

from PySide6 import QtCore
from PySide6.QtCore import QSortFilterProxyModel, QModelIndex
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QTreeView, QMenu, QWidget

from caqtus.session import ExperimentSessionMaker, PureSequencePath
from .async_model import AsyncPathHierarchyModel
from .delegate import ProgressDelegate


class AsyncPathHierarchyView(QTreeView):
    sequence_double_clicked = QtCore.Signal(PureSequencePath)

    def __init__(
        self, session_maker: ExperimentSessionMaker, parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.session_maker = session_maker
        self._model = AsyncPathHierarchyModel(session_maker, self)
        self._proxy_model = QSortFilterProxyModel(self)
        self._proxy_model.setSourceModel(self._model)
        self.setModel(self._proxy_model)
        self.setSortingEnabled(True)
        self.header().setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.header().customContextMenuRequested.connect(self.show_header_menu)
        self.doubleClicked.connect(self.on_double_click)
        self.sortByColumn(4, QtCore.Qt.SortOrder.AscendingOrder)
        self.hideColumn(4)
        self.setItemDelegateForColumn(1, ProgressDelegate(self))
        self.setUniformRowHeights(True)

    async def run_async(self) -> None:
        await self._model.run()

    def show_header_menu(self, pos):
        menu = QMenu(self)
        visibility_menu = menu.addMenu("Visible")
        # The first column is the name and should not be hidden.
        for column in range(1, self.model().columnCount()):
            action = QAction(
                self.model().headerData(column, QtCore.Qt.Orientation.Horizontal), self
            )
            action.setCheckable(True)
            action.setChecked(not self.isColumnHidden(column))
            action.triggered.connect(functools.partial(self.toggle_visibility, column))
            visibility_menu.addAction(action)
        menu.exec(self.mapToGlobal(pos))

    def toggle_visibility(self, column: int):
        column_hidden = self.isColumnHidden(column)
        self.setColumnHidden(column, not column_hidden)

    def on_double_click(self, index: QModelIndex):
        path = self._model.get_path(self._proxy_model.mapToSource(index))
        with self.session_maker() as session:
            is_sequence = session.sequences.is_sequence(path).unwrap()
        if is_sequence:
            self.sequence_double_clicked.emit(path)
