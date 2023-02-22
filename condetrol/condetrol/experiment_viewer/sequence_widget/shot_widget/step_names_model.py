import logging

from PyQt6.QtCore import (
    QModelIndex,
    Qt,
    QAbstractListModel,
)

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class StepNamesModel(QAbstractListModel):
    """Model for the names of the steps

    Note that while it is implemented as a list model with several rows, it is
    displayed horizontally at the top of the swim lane view.
    """

    def __init__(
        self,
        step_names: list[str],
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._step_names = step_names

    @property
    def step_names(self):
        return self._step_names

    @step_names.setter
    def step_names(self, step_names: step_names):
        self.beginResetModel()
        self._step_names = step_names
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self._step_names)

    def data(self, index: QModelIndex, role: int = ...):
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            return self._step_names[index.row()]

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return "Step"
            else:
                return f"Step {section}"

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEditable
        )

    def setData(self, index: QModelIndex, value: str, role: int = ...) -> bool:
        if role == Qt.ItemDataRole.EditRole:
            self._step_names[index.row()] = value
            self.dataChanged.emit(index, index, [role])
            return True
        else:
            return False

    def insertRow(self, row: int, parent: QModelIndex = ...) -> bool:
        if parent == ...:
            parent = QModelIndex()
        self.beginInsertRows(parent, row, row)
        self._step_names.insert(row, "...")
        self.endInsertRows()
        return True

    def removeRow(self, row: int, parent: QModelIndex = ...) -> bool:
        if parent == ...:
            parent = QModelIndex()
        self.beginRemoveRows(parent, row, row)
        self._step_names.pop(row)
        self.endRemoveRows()
        return True
