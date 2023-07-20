from types import NotImplementedType
from typing import Any

from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QWidget, QComboBox, QMenu

from lane.model import LaneModel
from tweezer_arranger.configuration import TweezerArrangerConfiguration
from tweezer_arranger_lane.configuration import (
    TweezerArrangerLane,
    HoldTweezers,
    MoveTweezers,
    TweezerAction,
    RearrangeTweezers,
)


class TweezerArrangerLaneModel(LaneModel[TweezerArrangerLane]):
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            return str(self.lane[index.row()])
        elif role == Qt.ItemDataRole.EditRole:
            return self.lane[index.row()]
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter

    def setData(
        self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole
    ) -> bool:
        if role == Qt.ItemDataRole.EditRole:
            if isinstance(value, TweezerAction):
                self.lane[index.row()] = value
                self.dataChanged.emit(index, index)
                return True
        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        cell_value = self.lane[index.row()]
        default_flags = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        if isinstance(cell_value, HoldTweezers):
            return default_flags | Qt.ItemFlag.ItemIsEditable
        else:
            return default_flags

    def create_editor(
        self, parent: QWidget, index: QModelIndex
    ) -> QWidget | NotImplementedType:
        if not index.isValid():
            return NotImplemented
        cell_value = self.data(index, Qt.ItemDataRole.EditRole)
        if isinstance(cell_value, HoldTweezers):
            combo_box = QComboBox(parent)
            arranger_config = self.experiment_config.get_device_config(self.lane.name)
            if not isinstance(arranger_config, TweezerArrangerConfiguration):
                raise TypeError(
                    f"Expected TweezerArrangerConfiguration, got {type(arranger_config)}"
                )
            for tweezer_config in arranger_config.keys():
                combo_box.addItem(tweezer_config)
            return combo_box
        return NotImplemented

    def set_editor_data(
        self, editor: QWidget, index: QModelIndex
    ) -> None | NotImplementedType:
        if not index.isValid():
            return NotImplemented
        cell_value = self.data(index, Qt.ItemDataRole.EditRole)
        if isinstance(cell_value, HoldTweezers):
            combo_box: QComboBox = editor  # type: ignore
            combo_box.setCurrentText(cell_value.configuration)
            return None
        return NotImplemented

    def get_editor_data(
        self, editor: QWidget, index: QModelIndex
    ) -> Any | NotImplementedType:
        if not index.isValid():
            return NotImplemented
        cell_value = self.data(index, Qt.ItemDataRole.EditRole)
        if isinstance(cell_value, HoldTweezers):
            combo_box: QComboBox = editor  # type: ignore
            cell_value.configuration = combo_box.currentText()
            return cell_value
        return NotImplemented

    def get_cell_context_actions(self, index: QModelIndex) -> list[QAction | QMenu]:
        menu = QMenu("tweezer")
        set_tweezer_static = menu.addAction("static")
        set_tweezer_static.triggered.connect(lambda: self._on_set_tweezer_static(index))
        set_tweezer_move = menu.addAction("move")
        set_tweezer_move.triggered.connect(lambda: self._on_set_tweezer_move(index))
        set_tweezer_rearrange = menu.addAction("rearrange")
        set_tweezer_rearrange.triggered.connect(
            lambda: self._on_set_tweezer_rearrange(index)
        )

        return [menu]

    def _on_set_tweezer_static(self, index: QModelIndex):
        self.setData(index, HoldTweezers.default())

    def _on_set_tweezer_move(self, index: QModelIndex):
        self.setData(index, MoveTweezers.default())

    def _on_set_tweezer_rearrange(self, index: QModelIndex):
        self.setData(index, RearrangeTweezers.default())
