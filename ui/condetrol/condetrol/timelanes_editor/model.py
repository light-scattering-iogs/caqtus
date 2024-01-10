import abc
import copy
from typing import Optional, Protocol, Any

from PyQt6.QtCore import (
    QAbstractTableModel,
    QObject,
    QModelIndex,
    QAbstractListModel,
    Qt,
)

from core.session.shot import TimeLane
from core.session.shot.timelane import TimeLanes
from core.types.expression import Expression
from qabc import qabc


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

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._names)

    def data(
        self, index: QModelIndex, role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole
    ):
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            return self._names[index.row()]


class TimeStepDurationModel(QAbstractListModel):
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._durations: list[Expression] = []

    def set_duration(self, durations: list[Expression]):
        self.beginResetModel()
        self._durations = copy.deepcopy(durations)
        self.endResetModel()

    def get_duration(self) -> list[Expression]:
        return copy.deepcopy(self._durations)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._durations)

    def data(
        self, index: QModelIndex, role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole
    ):
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            return self._durations[index.row()].body


class TimeLaneModel[L: TimeLane, O](QAbstractListModel, qabc.QABC):
    @abc.abstractmethod
    def __init__(self, name: str, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._name = name

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole,
    ):
        if orientation == Qt.Orientation.Horizontal:
            return self._name
        elif orientation == Qt.Orientation.Vertical:
            return section

    @abc.abstractmethod
    def set_lane(self, lane: L) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_lane(self) -> L:
        raise NotImplementedError

    @abc.abstractmethod
    def set_display_options(self, options: O) -> None:
        raise NotImplementedError


class LaneModelFactory(Protocol):
    def __call__[L: TimeLane](self, lane: L) -> type[TimeLaneModel[L, Any]]:
        ...


class TimeLanesModel(QAbstractTableModel, qabc.QABC):
    def __init__(
        self, lane_model_factory: LaneModelFactory, parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self._step_names_model = TimeStepNameModel(self)
        self._step_durations_model = TimeStepDurationModel(self)
        self._lane_models: list[TimeLaneModel] = []
        self._lane_model_factory = lane_model_factory

    def set_timelanes(self, timelanes: TimeLanes):
        new_models = []
        for name, lane in timelanes.lanes.items():
            lane_model = self._lane_model_factory(lane)(name, self)
            lane_model.set_lane(lane)
            new_models.append(lane_model)

        self.beginResetModel()
        self._step_names_model.set_names(timelanes.step_names)
        self._step_durations_model.set_duration(timelanes.step_durations)
        self._lane_models.clear()
        self._lane_models.extend(new_models)
        self.endResetModel()

    # @abc.abstractmethod
    # def get_lane_model_type[L](self, lane: L) -> type[TimeLaneModel[L]]:
    #     raise NotImplementedError

    def get_timelanes(self) -> TimeLanes:
        return TimeLanes(
            step_names=self._step_names_model.get_names(),
            step_durations=self._step_durations_model.get_duration(),
            lanes={name: lane.get_lane() for name, lane in self._lane_models.items()},
        )

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        count = self._step_names_model.rowCount()
        assert count == self._step_durations_model.rowCount()
        assert all(model.rowCount() == count for model in self._lane_models)
        return count

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._lane_models) + 2

    def data(self, index, role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        return self._map_to_source(index).data(role)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole,
    ):
        if orientation == Qt.Orientation.Horizontal:
            return f"Step {section}"
        elif orientation == Qt.Orientation.Vertical:
            if section == 0:
                if role == Qt.ItemDataRole.DisplayRole:
                    return "Step name"
            elif section == 1:
                if role == Qt.ItemDataRole.DisplayRole:
                    return "Step duration"
            else:
                return self._lane_models[section - 2].headerData(
                    0, Qt.Orientation.Horizontal, role
                )

    def _map_to_source(self, index: QModelIndex) -> QModelIndex:
        assert index.isValid()
        assert self.hasIndex(index.row(), index.column())
        if index.row() == 0:
            return self._step_names_model.index(index.column(), 0)
        elif index.row() == 1:
            return self._step_durations_model.index(index.column(), 0)
        else:
            return self._lane_models[index.row() - 2].index(index.column(), 0)
