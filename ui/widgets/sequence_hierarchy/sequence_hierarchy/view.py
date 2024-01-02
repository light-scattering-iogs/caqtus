import functools

from PyQt6 import QtCore
from PyQt6.QtCore import QSortFilterProxyModel
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QTreeView, QMenu

from core.session import ExperimentSessionMaker
from .model import PathHierarchyModel


class PathHierarchyView(QTreeView):
    def __init__(self, session_maker: ExperimentSessionMaker, parent=None):
        super().__init__(parent)
        self._model = PathHierarchyModel(session_maker, self)
        self._proxy_model = QSortFilterProxyModel(self)
        self._proxy_model.setSourceModel(self._model)
        self.setModel(self._proxy_model)
        self.setSortingEnabled(True)
        self.header().setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.header().customContextMenuRequested.connect(self.show_header_menu)

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

    def __enter__(self):
        self._model.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self._model.__exit__(exc_type, exc_value, traceback)
