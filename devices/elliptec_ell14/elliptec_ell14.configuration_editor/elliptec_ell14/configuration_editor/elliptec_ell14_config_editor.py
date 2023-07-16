from collections.abc import Collection

from device.configuration_editor import DeviceConfigEditor
from device_server.name import DeviceServerName
from elliptec_ell14.configuration import ElliptecELL14RotationStageConfiguration
from .elliptec_ell14_config_editor_ui import Ui_ElliptecELL14RotationStageConfigEditor


class ElliptecELL14RotationStageConfigEditor(
    DeviceConfigEditor[ElliptecELL14RotationStageConfiguration],
    Ui_ElliptecELL14RotationStageConfigEditor,
):
    def __init__(
        self,
        device_config: ElliptecELL14RotationStageConfiguration,
        available_remote_servers: Collection[DeviceServerName],
        *args,
        **kwargs,
    ):

        super().__init__(device_config, available_remote_servers, *args, **kwargs)
        self.setupUi(self)

        self.update_ui(self._device_config)

    def update_ui(self, device_config: ElliptecELL14RotationStageConfiguration):
        self._remote_server_combobox.set_servers(self._available_remote_servers)
        self._remote_server_combobox.set_current_server(device_config.remote_server)
        self._serial_port_widget.set_port(device_config.serial_port)
        self._device_id_spinbox.setValue(device_config.device_id)
        self._angle_line_edit.set_expression(device_config.position)

    def get_device_config(self) -> ElliptecELL14RotationStageConfiguration:
        config = super().get_device_config()
        config.remote_server = self._remote_server_combobox.get_current_server()
        config.serial_port = self._serial_port_widget.get_port()
        config.device_id = self._device_id_spinbox.value()
        config.position = self._angle_line_edit.get_expression()
        return config
