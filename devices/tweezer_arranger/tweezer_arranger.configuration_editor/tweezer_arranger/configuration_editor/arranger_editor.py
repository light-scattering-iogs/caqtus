from typing import Collection

from PyQt6.QtCore import QAbstractListModel, QModelIndex, Qt

from device.configuration_editor import DeviceConfigEditor
from device_server.name import DeviceServerName
from tweezer_arranger.configuration import TweezerArrangerConfiguration, TweezerConfigurationName
from .configuration_editor_ui import Ui_TweezerArrangerConfigEditor


class TweezerArrangerConfigEditor(
    Ui_TweezerArrangerConfigEditor, DeviceConfigEditor[TweezerArrangerConfiguration]
):
    """Widget to display the configurations of a tweezer arranger.

    This widget doesn't allow to edit the configurations, only to display them.
    """

    def __init__(
        self,
        device_config: TweezerArrangerConfiguration,
        available_remote_servers: Collection[DeviceServerName],
        *args,
        **kwargs,
    ):
        super().__init__(device_config, available_remote_servers, *args, **kwargs)
        self.setupUi(self)
        self.update_ui(device_config)

    def get_device_config(self) -> TweezerArrangerConfiguration:
        return self.list_view.model().config

    def update_ui(self, device_config: TweezerArrangerConfiguration):
        self.list_view.setModel(ArrangerModel(device_config))


class ArrangerModel(QAbstractListModel):
    def __init__(self, config: TweezerArrangerConfiguration, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.config = config

    @property
    def config(self) -> TweezerArrangerConfiguration:
        return self._config

    @config.setter
    def config(self, config: TweezerArrangerConfiguration) -> None:
        self.beginResetModel()
        self._config = config
        self._config_names = list(config.tweezer_configurations.keys())
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._config_names)

    def data(
        self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> TweezerConfigurationName | str | None:
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
