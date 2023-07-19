from types import NotImplementedType

from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtWidgets import QWidget, QComboBox

from lane.model import LaneModel
from tweezer_arranger.configuration import TweezerArrangerConfiguration
from tweezer_arranger_lane.configuration import TweezerArrangerLane, HoldTweezers


class TweezerArrangerLaneModel(LaneModel[TweezerArrangerLane]):
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            return self.lane[index.row()]

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

    def set_data_from_editor(
        self, editor: QWidget, index: QModelIndex
    ) -> None | NotImplementedType:
        if not index.isValid():
            return NotImplemented
        cell_value = self.data(index, Qt.ItemDataRole.EditRole)
        if isinstance(cell_value, HoldTweezers):
            combo_box: QComboBox = editor  # type: ignore
            cell_value.configuration = combo_box.currentText()
            return None
        return NotImplemented
