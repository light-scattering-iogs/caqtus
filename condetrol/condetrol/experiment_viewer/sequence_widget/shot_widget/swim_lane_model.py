import logging
from functools import singledispatch
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, QSize

from sequence import Step, ExecuteShot, SequenceStats, SequenceConfig
from shot import ShotConfiguration
from ..sequence_watcher import SequenceWatcher

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class SwimLaneModel(QAbstractTableModel):
    """Model for a shot parallel time steps

    Each column corresponds to a time step.
    Row 0 corresponds to the name of the time steps and Row 1 corresponds to the
    duration of the steps. Other rows are device lanes.
    """

    def __init__(self, sequence_path: Path, shot_name: str):
        super().__init__()
        self.config_path = sequence_path / "sequence_config.yaml"
        self.state_path = sequence_path / "sequence_state.yaml"

        self.shot_name = shot_name
        self.sequence_watcher = SequenceWatcher(sequence_path)
        self.sequence_config = self.sequence_watcher.read_config()
        self.sequence_state = self.sequence_watcher.read_stats().state
        self.shot_config = find_shot_config(
            self.sequence_config.program, self.shot_name
        )
        self.layoutChanged.emit()

        self.sequence_watcher.config_changed.connect(self.change_sequence_config)
        self.sequence_watcher.stats_changed.connect(self.change_sequence_state)

        logger.debug(self.shot_config)

    def change_sequence_state(self, stats: SequenceStats):
        self.sequence_state = stats.state
        self.layoutChanged.emit()

    def change_sequence_config(self, sequence_config: SequenceConfig):
        self.sequence_config = sequence_config
        self.shot_config = find_shot_config(
            self.sequence_config.program, self.shot_name
        )
        self.layoutChanged.emit()

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return 2 + len(self.shot_config.lanes)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return len(self.shot_config.step_names)

    def data(self, index: QModelIndex, role: int = ...):
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            if index.row() == 0:
                return self.shot_config.step_names[index.column()]
            elif index.row() == 1:
                return self.shot_config.step_durations[index.column()].body
            else:
                return self.shot_config.lanes[index.row() - 2].values[index.column()]

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return f"Step {section}"
            elif orientation == Qt.Orientation.Vertical:
                if section == 0:
                    return "Name"
                elif section == 1:
                    return "Duration"
                else:
                    return self.shot_config.lanes[section - 2].name

    def span(self, index: QModelIndex) -> QSize:
        if index.row() <= 1:
            return QSize(1, 1)
        else:
            return QSize(
                self.shot_config.lanes[index.row() - 2].spans[index.column()], 1
            )


@singledispatch
def find_shot_config(step: Step, shot_name: str) -> Optional[ShotConfiguration]:
    for sub_step in step.children:
        if result := find_shot_config(sub_step, shot_name):
            return result


@find_shot_config.register
def _(shot: ExecuteShot, shot_name):
    if shot.name == shot_name:
        return shot.configuration
