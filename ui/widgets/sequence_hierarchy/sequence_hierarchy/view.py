from PyQt6.QtCore import QSortFilterProxyModel
from PyQt6.QtWidgets import QTreeView

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

    def __enter__(self):
        self._model.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self._model.__exit__(exc_type, exc_value, traceback)
