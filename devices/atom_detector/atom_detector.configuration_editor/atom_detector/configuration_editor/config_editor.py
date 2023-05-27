from typing import Collection

from atom_detector.configuration import AtomDetectorConfiguration
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
        **kwargs
    ):
        super().__init__(device_config, available_remote_servers, *args, **kwargs)
        self.setupUi(self)

    def get_device_config(self) -> AtomDetectorConfiguration:
        return super().get_device_config()
