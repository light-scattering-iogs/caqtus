from types import NotImplementedType
from typing import TypeVar, Generic, Any, Optional

from PyQt6.QtCore import QAbstractListModel, QModelIndex, Qt, QSize
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QWidget, QMenu

from experiment.configuration import ExperimentConfig
from lane.configuration import Lane

LaneType = TypeVar("LaneType", bound=Lane)


class LaneModel(QAbstractListModel, Generic[LaneType]):
    def __init__(
        self, lane: LaneType, experiment_config: ExperimentConfig, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.lane = lane
        self.experiment_config = experiment_config

    @property
    def lane(self):
        return self._lane

    @lane.setter
    def lane(self, lane: LaneType):
        self.beginResetModel()
        self._lane = lane
        self.endResetModel()

    @property
    def experiment_config(self):
        return self._experiment_config

    @experiment_config.setter
    def experiment_config(self, experiment_config: ExperimentConfig):
        self.beginResetModel()
        self._experiment_config = experiment_config
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.lane)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Optional[str]:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.lane.name
            else:
                return str(section)

    def span(self, index: QModelIndex) -> QSize:
        return QSize(self.lane.spans[index.row()], 1)

    def removeRow(self, row: int, parent: QModelIndex = QModelIndex()) -> bool:
        self.beginRemoveRows(parent, row, row)
        self.lane.remove(row)
        self.endRemoveRows()
        return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if self.lane.spans[index.row()] > 0:
            return (
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsEditable
                | Qt.ItemFlag.ItemIsSelectable
            )
        else:
            return Qt.ItemFlag.ItemIsSelectable

    def merge(self, start, stop):
        self.beginResetModel()
        self.lane.merge(start, stop)
        self.endResetModel()

    def break_up(self, start, stop):
        self.beginResetModel()
        self.lane.break_(start, stop)
        self.endResetModel()

    def create_editor(
        self, parent: QWidget, index: QModelIndex
    ) -> QWidget | NotImplementedType:
        return NotImplemented

    def set_editor_data(
        self, editor: QWidget, index: QModelIndex
    ) -> None | NotImplementedType:
        return NotImplemented

    def get_editor_data(
        self, editor: QWidget, index: QModelIndex
    ) -> Any | NotImplementedType:
        return NotImplemented

    def get_cell_context_actions(self, index: QModelIndex) -> list[QAction | QMenu]:
        return []
