# Ignore some lint rules for this file as PySide6 models have a lot of camelCase
# methods.
# ruff: noqa: N802
import copy
from typing import Optional

from PySide6.QtCore import (
    QAbstractListModel,
    QObject,
    QModelIndex,
    Qt,
)
from PySide6.QtGui import QFont

from caqtus.types.expression import Expression

_DEFAULT_INDEX = QModelIndex()


class TimeStepNameModel(QAbstractListModel):
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._names: list[str] = []

    def set_names(self, names: list[str]):
        self.beginResetModel()
        self._names = copy.deepcopy(names)
        self.endResetModel()

    def get_names(self) -> list[str]:
        return copy.deepcopy(self._names)

    def rowCount(self, parent=_DEFAULT_INDEX) -> int:
        return len(self._names)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            return self._names[index.row()]
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid():
            return False
        if role == Qt.ItemDataRole.EditRole:
            if not isinstance(value, str):
                raise TypeError(f"Expected str, got {type(value)}")
            self._names[index.row()] = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable

    def insertRow(self, row, parent=_DEFAULT_INDEX) -> bool:
        if not (0 <= row <= self.rowCount()):
            return False
        self.beginInsertRows(parent, row, row)
        self._names.insert(row, f"Step {row}")
        self.endInsertRows()
        return True

    def removeRow(self, row, parent=_DEFAULT_INDEX) -> bool:
        if not (0 <= row < self.rowCount()):
            return False
        self.beginRemoveRows(parent, row, row)
        del self._names[row]
        self.endRemoveRows()
        return True

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return "Step names"
            elif orientation == Qt.Orientation.Vertical:
                return section
        elif role == Qt.ItemDataRole.FontRole:
            font = QFont()
            font.setBold(True)
            return font


class TimeStepDurationModel(QAbstractListModel):
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._durations: list[Expression] = []

    def set_durations(self, durations: list[Expression]):
        self.beginResetModel()
        self._durations = copy.deepcopy(durations)
        self.endResetModel()

    def get_duration(self) -> list[Expression]:
        return copy.deepcopy(self._durations)

    def rowCount(self, parent=_DEFAULT_INDEX) -> int:
        return len(self._durations)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            return self._durations[index.row()].body
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid():
            return False
        if role == Qt.ItemDataRole.EditRole:
            if not isinstance(value, str):
                raise TypeError(f"Expected str, got {type(value)}")
            self._durations[index.row()] = Expression(value)
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable

    def insertRow(self, row, parent=_DEFAULT_INDEX) -> bool:
        if not (0 <= row <= self.rowCount()):
            return False
        self.beginInsertRows(parent, row, row)
        self._durations.insert(row, Expression("..."))
        self.endInsertRows()
        return True

    def removeRow(self, row, parent=_DEFAULT_INDEX) -> bool:
        if not (0 <= row < self.rowCount()):
            return False
        self.beginRemoveRows(parent, row, row)
        del self._durations[row]
        self.endRemoveRows()
        return True

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return "Step durations"
            elif orientation == Qt.Orientation.Vertical:
                return section
        elif role == Qt.ItemDataRole.FontRole:
            font = QFont()
            font.setBold(True)
            return font
