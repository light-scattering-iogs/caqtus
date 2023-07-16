from collections.abc import Collection

from device.configuration_editor import DeviceConfigEditor
from device_server.name import DeviceServerName
from orca_quest.configuration import OrcaQuestCameraConfiguration
from .orca_quest_config_editor_ui import Ui_OrcaQuestConfigEditor


class OrcaQuestConfigEditor(
    DeviceConfigEditor[OrcaQuestCameraConfiguration], Ui_OrcaQuestConfigEditor
):
    def __init__(
        self,
        device_config: OrcaQuestCameraConfiguration,
        available_remote_servers: Collection[DeviceServerName],
        *args,
        **kwargs,
    ):

        super().__init__(device_config, available_remote_servers, *args, **kwargs)
        self.setupUi(self)
        self.update_ui(self._device_config)

    def update_ui(self, device_config: OrcaQuestCameraConfiguration):
        self._remote_server_combobox.set_servers(list(self._available_remote_servers))
        self._remote_server_combobox.set_current_server(device_config.remote_server)
        self._camera_number_spinbox.setValue(device_config.camera_number)
        self._left_spinbox.setRange(0, device_config.roi.original_width - 1)
        self._left_spinbox.setValue(device_config.roi.left)

        self._right_spinbox.setRange(0, device_config.roi.original_width - 1)
        self._right_spinbox.setValue(device_config.roi.right)

        self._bottom_spinbox.setRange(0, device_config.roi.original_height - 1)
        self._bottom_spinbox.setValue(device_config.roi.bottom)

        self._top_spinbox.setRange(0, device_config.roi.original_height - 1)
        self._top_spinbox.setValue(device_config.roi.top)

    def get_device_config(self) -> OrcaQuestCameraConfiguration:
        device_config = super().get_device_config()
        device_config.remote_server = self._remote_server_combobox.get_current_server()
        device_config.camera_number = self._camera_number_spinbox.value()
        device_config.roi.x = self._left_spinbox.value()
        device_config.roi.width = (
            self._right_spinbox.value() - self._left_spinbox.value() + 1
        )
        device_config.roi.y = self._bottom_spinbox.value()
        device_config.roi.height = (
            self._top_spinbox.value() - self._bottom_spinbox.value() + 1
        )
        return device_config
