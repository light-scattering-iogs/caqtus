import logging

from PyQt6.QtCore import (
    QModelIndex,
    Qt,
    QAbstractListModel,
)

from expression import Expression

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class StepDurationsModel(QAbstractListModel):
    """Model for the durations of the steps

    Note that while it is implemented as a list model with several rows, it is
    displayed horizontally as the second line of the swim lane view.
    """

    def __init__(self, step_durations: list[Expression], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._step_durations = step_durations

    @property
    def step_durations(self):
        return self._step_durations

    @step_durations.setter
    def step_durations(self, step_durations: list[Expression]):
        self.beginResetModel()
        self._step_durations = step_durations
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self._step_durations)

    def data(self, index: QModelIndex, role: int = ...) -> str:
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            return self._step_durations[index.row()].body

    def setData(self, index: QModelIndex, value: str, role: int = ...) -> bool:
        if role == Qt.ItemDataRole.EditRole:
            previous = self._step_durations[index.row()].body
            try:
                self._step_durations[index.row()].body = value
            except SyntaxError as error:
                logger.error(error.msg)
                self._step_durations[index.column()].body = previous
                return False
            return True
        else:
            return False

    def insertRow(self, row: int, parent: QModelIndex = ...) -> bool:
        if parent == ...:
            parent = QModelIndex()
        self.beginInsertRows(parent, row, row)
        self._step_durations.insert(row, Expression("..."))
        self.endInsertRows()
        return True

    def removeRow(self, row: int, parent: QModelIndex = ...) -> bool:
        if parent == ...:
            parent = QModelIndex()
        self.beginRemoveRows(parent, row, row)
        self._step_durations.pop(row)
        self.endRemoveRows()
        return True
