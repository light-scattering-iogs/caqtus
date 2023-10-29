from typing import TypeVar

from PyQt6.QtCore import QModelIndex, Qt

from .mapping_model import MappingModel

_K = TypeVar("_K")
_V = TypeVar("_V")


class MutableMappingModel(MappingModel[_K, _V]):
    """A model that can be used to edit a mapping in a QTableView.

    This model has two columns: the first column contains the keys of the mapping, the second column contains the values
    of the mapping. The number of rows is equal to the number of items in the mapping.

    This model doesn't store a reference to the initial mapping, but copies it. This means that changes to the mapping
    passed to set_mapping will not be reflected in the model and vice versa.
    """

    def data(
        self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> _K | _V | None:
        if role == Qt.ItemDataRole.EditRole or role == Qt.ItemDataRole.DisplayRole:
            return super().data(index, Qt.ItemDataRole.DisplayRole)
        return super().data(index, role)

    def setData(
        self, index: QModelIndex, value: _K | _V, role: int = Qt.ItemDataRole.EditRole
    ) -> bool:
        if not index.isValid():
            return False
        if role == Qt.ItemDataRole.EditRole:
            if index.column() == 0:
                self._keys[index.row()] = value
            elif index.column() == 1:
                self._values[index.row()] = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEditable
        )

    def insert_row(self, row: int, key: _K, value: _V) -> bool:
        """Insert a row into the model."""

        if row < 0 or row > self.rowCount():
            return False

        if key in self._keys:
            return False

        self.beginInsertRows(QModelIndex(), row, row)
        self._keys.insert(row, key)
        self._values.insert(row, value)
        self.endInsertRows()
        return True

    def removeRows(
        self, row: int, count: int, parent: QModelIndex = QModelIndex()
    ) -> bool:
        """Remove rows from the model."""

        if row < 0 or row + count > self.rowCount() or count < 0:
            return False
        self.beginRemoveRows(parent, row, row + count - 1)
        del self._keys[row : row + count]
        del self._values[row : row + count]
        self.endRemoveRows()
        return True
