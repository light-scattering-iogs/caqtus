from PyQt6.QtCore import QModelIndex, Qt

from atom_detector_lane.configuration import AtomDetectorLane
from lane.model import LaneModel


class AtomDetectorLaneModel(LaneModel[AtomDetectorLane]):
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            return str(self.lane[index.row()])
        elif role == Qt.ItemDataRole.EditRole:
            return self.lane[index.row()]
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter

    def setData(self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if role == Qt.ItemDataRole.EditRole:
            self.lane[index.row()] = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        cell_value = self.lane[index.row()]
        default_flags = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        if isinstance(cell_value, str):
            return default_flags | Qt.ItemFlag.ItemIsEditable
        return default_flags

    def insertRow(self, row: int, parent: QModelIndex = QModelIndex()) -> bool:
        self.beginInsertRows(parent, row, row)
        self.lane.insert(row, None)
        self.endInsertRows()
        return True
