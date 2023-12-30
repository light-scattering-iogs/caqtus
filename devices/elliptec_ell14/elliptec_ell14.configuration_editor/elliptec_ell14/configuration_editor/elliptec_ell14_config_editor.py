from condetrol.device_configuration_editor import DeviceConfigurationEditor
from core.configuration import Expression
from elliptec_ell14.configuration import ElliptecELL14RotationStageConfiguration
from .elliptec_ell14_config_editor_ui import Ui_ElliptecELL14RotationStageConfigEditor


class ElliptecELL14RotationStageConfigurationEditor(
    DeviceConfigurationEditor[ElliptecELL14RotationStageConfiguration],
    Ui_ElliptecELL14RotationStageConfigEditor,
):
    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        device_configuration = ElliptecELL14RotationStageConfiguration(
            serial_port="COM0",
            device_id=0,
            position=Expression("0"),
        )
        self.set_configuration(device_configuration)

    def set_configuration(
        self, device_configuration: ElliptecELL14RotationStageConfiguration
    ) -> None:
        self._serial_port_widget.set_port(device_configuration.serial_port)
        self._device_id_spinbox.setValue(device_configuration.device_id)
        self._angle_line_edit.setText(device_configuration.position.body)

    def get_configuration(self) -> ElliptecELL14RotationStageConfiguration:
        device_configuration = ElliptecELL14RotationStageConfiguration(
            serial_port=self._serial_port_widget.get_port(),
            device_id=self._device_id_spinbox.value(),
            position=Expression(self._angle_line_edit.text()),
        )
        return device_configuration
