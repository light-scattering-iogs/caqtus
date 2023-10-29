from typing import Mapping, TypeVar, Generic

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt

_K = TypeVar("_K")
_V = TypeVar("_V")


class MappingModel(QAbstractTableModel, Generic[_K, _V]):
    """A model that can be used to display a mapping in a QTableView.

    This class only implements the bare minimum required to display a mapping in a QTableView. It does not implement
    any editing functionality.
    This model has two columns: the first column contains the keys of the mapping, the second column contains the values
    of the mapping. The number of rows is equal to the number of items in the mapping.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._keys: list[_K] = []
        self._values: list[_V] = []

    def set_mapping(self, mapping: Mapping[_K, _V]) -> None:
        """Set the mapping to be displayed by the model."""

        self.beginResetModel()
        self._keys = list(mapping.keys())
        self._values = list(mapping.values())
        self.endResetModel()

    def get_mapping(self) -> dict[_K, _V]:
        """Return a copy of the mapping displayed by the model.

        Note that this method returns a dictionary, which is not necessarily the same type as the mapping passed to
        set_mapping.
        """

        return {key: value for key, value in zip(self._keys, self._values)}

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._keys)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 2

    def data(
        self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> _K | _V | None:
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == 0:
                return self._keys[index.row()]
            elif index.column() == 1:
                return self._values[index.row()]
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if section == 0:
                    return "Key"
                elif section == 1:
                    return "Value"
            elif orientation == Qt.Orientation.Vertical:
                return str(section)
        return super().headerData(section, orientation, role)
