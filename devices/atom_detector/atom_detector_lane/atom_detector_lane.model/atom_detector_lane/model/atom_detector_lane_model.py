from types import NotImplementedType
from typing import Any

from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu, QWidget, QComboBox

from atom_detector.configuration import ImagingConfigurationName, AtomDetectorConfiguration
from atom_detector_lane.configuration import AtomDetectorLane
from lane.model import LaneModel


class AtomDetectorLaneModel(LaneModel[AtomDetectorLane]):
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            cell_value = self.lane[index.row()]
            if cell_value is None:
                return ""
            return str(self.lane[index.row()])
        elif role == Qt.ItemDataRole.EditRole:
            return self.lane[index.row()]
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter

    def setData(
        self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole
    ) -> bool:
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

    def get_cell_context_actions(self, index: QModelIndex) -> list[QAction | QMenu]:
        menu = QMenu("detector")
        set_do_nothing = menu.addAction("do nothing")
        set_do_nothing.triggered.connect(lambda: self._on_set_do_nothing(index))
        set_analyze_image = menu.addAction("analyze picture")
        set_analyze_image.triggered.connect(lambda: self._on_set_analyze_image(index))

        return [menu]

    def _on_set_do_nothing(self, index: QModelIndex):
        self.setData(index, None)

    def _on_set_analyze_image(self, index: QModelIndex):
        self.setData(index, ImagingConfigurationName("..."))

    def create_editor(
        self, parent: QWidget, index: QModelIndex
    ) -> QWidget | NotImplementedType:
        if not index.isValid():
            return NotImplemented
        cell_value = self.data(index, Qt.ItemDataRole.EditRole)
        if isinstance(cell_value, str):
            combo_box = QComboBox(parent)
            device_config = self.experiment_config.get_device_config(self.lane.name)
            if not isinstance(device_config, AtomDetectorConfiguration):
                raise TypeError(
                    f"Expected AtomDetectorConfiguration, got {type(device_config)}"
                )
            for detector_config in device_config.keys():
                combo_box.addItem(detector_config)
            return combo_box
        return NotImplemented

    def set_editor_data(
        self, editor: QWidget, index: QModelIndex
    ) -> None | NotImplementedType:
        if not index.isValid():
            return NotImplemented
        cell_value = self.data(index, Qt.ItemDataRole.EditRole)
        if isinstance(cell_value, str):
            combo_box: QComboBox = editor  # type: ignore
            combo_box.setCurrentText(cell_value)
            return None
        return NotImplemented

    def get_editor_data(
        self, editor: QWidget, index: QModelIndex
    ) -> Any | NotImplementedType:
        if not index.isValid():
            return NotImplemented
        cell_value = self.data(index, Qt.ItemDataRole.EditRole)
        if isinstance(cell_value, str):
            combo_box: QComboBox = editor  # type: ignore
            cell_value = combo_box.currentText()
            return cell_value
        return NotImplemented
