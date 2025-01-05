from __future__ import annotations

import functools
import logging
from collections.abc import Mapping, Iterable, Callable
from typing import Optional

import attrs
from PySide6.QtCore import (
    Qt,
    QModelIndex,
    QAbstractTableModel,
    QObject,
    QPersistentModelIndex,
    Signal,
    Slot,
)
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QDialogButtonBox,
    QLineEdit,
    QVBoxLayout,
    QGroupBox,
)

from caqtus.device import DeviceConfiguration, DeviceName
from caqtus.device.configuration import DeviceServerName
from ._add_device_dialog_ui import Ui_AddDeviceDialog
from ._device_configuration_editor import (
    DeviceConfigurationEditor,
)
from ._device_configurations_dialog_ui import Ui_DeviceConfigurationsDialog
from ._extension import CondetrolDeviceExtensionProtocol
from .._icons import get_icon

logger = logging.getLogger(__name__)

_CONFIG_ROLE = Qt.ItemDataRole.UserRole + 1
_DEFAULT_MODEL_INDEX = QModelIndex()


class DeviceConfigurationsDialog(QDialog, Ui_DeviceConfigurationsDialog):
    """A dialog for displaying and editing a collection of device configurations."""

    def __init__(
        self,
        extension: CondetrolDeviceExtensionProtocol,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the dialog."""

        super().__init__(parent, Qt.WindowType.Window)
        self.setup_ui()
        # self._configs_view = DeviceConfigurationsEditor(extension, self)
        self.add_device_dialog = AddDeviceDialog(extension, self)
        self._model = DeviceModel(self)
        self._mapper = ModelWidgetMapper(self._model, self)
        # self._mapper.setSubmitPolicy(QDataWidgetMapper.SubmitPolicy.ManualSubmit)
        # self._mapper.setModel(self._model)
        self._remote_server_editor = DeviceServerEditor(self)
        self.form_layout.addRow("Remote Server", self._remote_server_editor)
        self._mapper.add_mapping(
            0,
            self.deviceNameLineEdit.text,
            self.deviceNameLineEdit.setText,
            self.deviceNameLineEdit.textEdited,
        )
        self._mapper.add_mapping(
            1,
            self._remote_server_editor.get_value,
            self._remote_server_editor.set_value,
        )

        self._config_editor = ConfigEditor(extension, self)
        layout = self.device_widget.layout()
        assert isinstance(layout, QVBoxLayout)
        layout.addWidget(self._config_editor)
        layout.addStretch()
        self._mapper.add_mapping(
            2, self._config_editor.get_config, self._config_editor.set_config
        )
        self._mapper.index_valid.connect(self.device_widget.setVisible)

        self.listView.setModel(self._model)
        self._extension = extension
        self.setup_connections()

    def setup_ui(self):
        self.setupUi(self)
        self.add_device_button.setIcon(get_icon("plus"))
        self.remove_device_button.setIcon(get_icon("minus"))

    def setup_connections(self):
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.add_device_button.clicked.connect(self._on_add_configuration)
        self.remove_device_button.clicked.connect(self._on_remove_device_clicked)
        self.listView.selectionModel().currentRowChanged.connect(self._on_row_changed)

    def _on_row_changed(self, current: QModelIndex, previous: QModelIndex):
        if current.isValid():
            self._mapper.set_current_row(current.row())

    def _on_remove_device_clicked(self) -> None:
        index = self.listView.currentIndex()
        if index.isValid():
            self._model.removeRow(index.row())

    def _on_add_configuration(self) -> None:
        result = self.add_device_dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            device_name, device_type = (
                self.add_device_dialog.device_name_line_edit.text(),
                self.add_device_dialog.device_type_combo_box.currentText(),
            )
            if not device_name:
                return
            device_configuration = self._extension.create_new_device_configuration(
                device_type
            )
            self._model.add_configuration(DeviceName(device_name), device_configuration)

    def get_device_configurations(self) -> dict[DeviceName, DeviceInfo]:
        self._mapper.submit()
        result = {
            name: DeviceInfo(config=config, device_server=server)
            for name, (server, config) in self._model.get_devices().items()
        }
        return result

    def set_device_configurations(
        self, device_configurations: Mapping[DeviceName, DeviceInfo]
    ) -> None:
        self._model.set_devices(
            {
                name: (info.device_server, info.config)
                for name, info in device_configurations.items()
            }
        )


class ConfigEditor(QGroupBox):
    def __init__(
        self,
        extension: CondetrolDeviceExtensionProtocol,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._editor: Optional[DeviceConfigurationEditor] = None
        self._extension = extension
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)
        self.setTitle("Configuration")

    def get_config(self):
        assert self._editor is not None
        return self._editor.get_configuration()

    def set_config(self, config: DeviceConfiguration):
        if self._editor is not None:
            self._layout.removeWidget(self._editor)
            self._editor.deleteLater()

        self._editor = self._extension.get_device_configuration_editor(config)
        self._layout.addWidget(self._editor)


@attrs.define
class DeviceInfo:
    """Contains information about a device."""

    config: DeviceConfiguration
    device_server: Optional[DeviceServerName]


class AddDeviceDialog(QDialog, Ui_AddDeviceDialog):
    def __init__(
        self,
        extension: CondetrolDeviceExtensionProtocol,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setup_ui(extension.available_new_configurations())

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.device_type_combo_box.currentTextChanged.connect(
            self._on_device_type_changed
        )
        self._on_device_type_changed(self.device_type_combo_box.currentText())

    def _on_device_type_changed(self, device_type: str):
        ok_button = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        assert ok_button is not None
        ok_button.setEnabled(bool(device_type))

    def setup_ui(self, device_types: Iterable[str]):
        self.setupUi(self)
        for device_type in device_types:
            self.device_type_combo_box.addItem(device_type)


class DeviceServerEditor(QLineEdit):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setPlaceholderText("None")

    def get_value(self) -> Optional[DeviceServerName]:
        text = self.text()
        return DeviceServerName(text) if text else None

    def set_value(self, value: Optional[DeviceServerName]):
        self.setText(value or "")


class DeviceModel(QAbstractTableModel):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._data: list[
            tuple[DeviceName, Optional[DeviceServerName], DeviceConfiguration]
        ] = []

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return 3

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        column = index.column()
        if role == Qt.ItemDataRole.DisplayRole:
            return self._data[row][column]
        elif role == Qt.ItemDataRole.EditRole:
            return self._data[row][column]

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid():
            return False
        row = index.row()
        column = index.column()
        if role == Qt.ItemDataRole.EditRole:
            if column == 0:
                self._data[row] = (value, self._data[row][1], self._data[row][2])
                self.dataChanged.emit(index, index)
                return True
            elif column == 1:
                self._data[row] = (self._data[row][0], value, self._data[row][2])
                self.dataChanged.emit(index, index)
                return True
            elif column == 2:
                self._data[row] = (self._data[row][0], self._data[row][1], value)
                self.dataChanged.emit(index, index)
                return True
        return False

    def flags(self, index):
        return (
            Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsEditable
        )

    def set_devices(
        self,
        device_configurations: Mapping[
            DeviceName, tuple[Optional[DeviceServerName], DeviceConfiguration]
        ],
    ) -> None:
        self.beginResetModel()
        self._data = [
            (name, server, config)
            for name, (server, config) in device_configurations.items()
        ]
        self.endResetModel()

    def get_devices(
        self,
    ) -> dict[DeviceName, tuple[Optional[DeviceServerName], DeviceConfiguration]]:
        return {name: (server, config) for name, server, config in self._data}

    def add_configuration(
        self, device_name: DeviceName, device_configuration: DeviceConfiguration
    ) -> None:
        self.beginInsertRows(
            QModelIndex(),
            len(self._data),
            len(self._data),
        )
        self._data.append((device_name, None, device_configuration))
        self.endInsertRows()

    def removeRow(self, row, parent=_DEFAULT_MODEL_INDEX):
        self.beginRemoveRows(parent, row, row)
        del self._data[row]
        self.endRemoveRows()
        return True


class ModelWidgetMapper(QObject):
    index_valid = Signal(bool)

    def __init__(self, model: QAbstractTableModel, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._model = model
        self._current_index: QPersistentModelIndex = QPersistentModelIndex()
        self._getters: dict[int, Callable] = {}
        self._setters: dict[int, Callable] = {}
        self._data_changed_connection = self._model.dataChanged.connect(
            self._on_data_changed
        )
        self._model.rowsRemoved.connect(self._on_rows_removed)
        self._model.modelReset.connect(self._on_model_reset)

    @Slot(QModelIndex, QModelIndex)
    def _on_data_changed(self, top_left, bottom_right):
        if not self._current_index.isValid():
            return
        current_row = self._current_index.row()
        if top_left.row() <= current_row <= bottom_right.row():
            for column in range(top_left.column(), bottom_right.column() + 1):
                data = self._model.data(
                    self._model.index(current_row, column), Qt.ItemDataRole.EditRole
                )
                self._setters[column](data)

    def _on_model_reset(self):
        self._current_index = QPersistentModelIndex()
        self.index_valid.emit(False)

    def _on_rows_removed(self, parent, first, last):
        if first <= self._current_index.row() <= last:
            self._current_index = QPersistentModelIndex()
            self.index_valid.emit(False)

    def submit(self):
        """Writes the data from the current editor to the model."""

        if self._current_index.isValid():
            row = self._current_index.row()
            for column, getter in self._getters.items():
                data = getter()
                self._model.setData(
                    self._model.index(row, column), data, Qt.ItemDataRole.EditRole
                )

    def update(self):
        """Updates the editor with the data from the current row in the model."""

        if self._current_index.isValid():
            row = self._current_index.row()
            for column, setter in self._setters.items():
                data = self._model.data(
                    self._model.index(row, column), Qt.ItemDataRole.EditRole
                )
                setter(data)

    def set_current_row(self, row: int) -> None:
        self.submit()
        self._current_index = QPersistentModelIndex(self._model.index(row, 0))
        self.index_valid.emit(self._current_index.isValid())
        self.update()

    def add_mapping[
        T
    ](
        self,
        column: int,
        getter: Callable[[], T],
        setter: Callable[[T], None],
        edit_trigger=None,
    ):
        self._getters[column] = getter
        self._setters[column] = setter
        if edit_trigger is not None:
            edit_trigger.connect(functools.partial(self._on_edited, column))

    def _on_edited(self, column: int, *args, **kwargs):
        if self._current_index.isValid():
            getter = self._getters[column]
            value = getter()
            self._model.setData(
                self._model.index(self._current_index.row(), column),
                value,
                Qt.ItemDataRole.EditRole,
            )
