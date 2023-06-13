from typing import Collection

from PyQt6.QtCore import QAbstractListModel, QModelIndex, Qt

from atom_detector.configuration import AtomDetectorConfiguration, ConfigurationName
from device.configuration_editor import ConfigEditor
from device_server.name import DeviceServerName
from .configuration_editor_ui import Ui_AtomDetectorConfigEditor


class AtomDetectorConfigEditor(
    Ui_AtomDetectorConfigEditor, ConfigEditor[AtomDetectorConfiguration]
):
    def __init__(
        self,
        device_config: AtomDetectorConfiguration,
        available_remote_servers: Collection[DeviceServerName],
        *args,
        **kwargs,
    ):
        super().__init__(device_config, available_remote_servers, *args, **kwargs)
        self.setupUi(self)
        self.set_configuration(device_config)

    def set_configuration(self, config: AtomDetectorConfiguration):
        self.list_view.setModel(ConfigurationModel(config))

    def get_device_config(self) -> AtomDetectorConfiguration:
        return self.list_view.model().config


class ConfigurationModel(QAbstractListModel):
    def __init__(self, config: AtomDetectorConfiguration, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.config = config

    @property
    def config(self) -> AtomDetectorConfiguration:
        return self._config

    @config.setter
    def config(self, config: AtomDetectorConfiguration) -> None:
        self.beginResetModel()
        self._config = config
        self._config_names = list(config.detector_configurations.keys())
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._config_names)

    def data(
        self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> ConfigurationName | str | None:
        if not index.isValid():
            return None
        name = self._config_names[index.row()]
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            return name
        elif role == Qt.ItemDataRole.ToolTipRole:
            modification_date = self._config.get_modification_date(name)
            trap_config = self._config.get_configuration(name)
            return f"Number traps: {len(trap_config)}\nModification date: {modification_date:%Y-%m-%d %H:%M:%S}"

        return None

    def setData(
        self, index: QModelIndex, value: str, role: int = Qt.ItemDataRole.EditRole
    ) -> bool:
        if not index.isValid():
            return False
        if role == Qt.ItemDataRole.EditRole:
            value = ConfigurationName(value)
            old_name = self._config_names[index.row()]
            config = self._config.get_configuration(old_name)
            self._config.remove_configuration(old_name)
            self._config.set_configuration(value, config)
            self._config_names[index.row()] = value

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
