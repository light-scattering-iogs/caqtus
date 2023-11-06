import logging
from typing import Any, Self

from device.configuration import DeviceConfigurationAttrs, DeviceParameter
from expression import Expression
from settings_model import YAMLSerializable
from units import units
from util import attrs

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@attrs.define(slots=False)
class ElliptecELL14RotationStageConfiguration(DeviceConfigurationAttrs):
    """Holds static configuration to control an ELL14 rotation stage device

    Attributes:
        serial_port: The serial port to use to communicate with the device.
            e.g. "COM9"
        device_id: The ID of the device. This is what is referred as the
            address in the thorlabs Ello software. If the device is used in multi-port
            mode, a single serial port can control multiple devices with different
            device IDs. However, this is not supported at the moment and only one device
            can be instantiated for a given serial port.
        position: The position of the stage in degrees. This can be an expression that
            depends on other variables. When these variables change, the new position
            will be recalculated in consequence and the stage will move to the new
            position.
    """

    serial_port: str = attrs.field(converter=str, on_setattr=attrs.setters.convert)
    device_id: int = attrs.field(
        converter=int,
        validator=[attrs.validators.ge(0), attrs.validators.le(255)],
        on_setattr=attrs.setters.pipe(attrs.setters.convert, attrs.setters.validate),
    )
    position: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )

    def get_device_type(self) -> str:
        return "ElliptecELL14RotationStage"

    def get_device_init_args(self) -> dict[DeviceParameter, Any]:
        extra = {
            DeviceParameter("serial_port"): self.serial_port,
            DeviceParameter("device_id"): self.device_id,
        }
        dependent_variables = self.position.upstream_variables.difference(units.keys())
        if dependent_variables:
            logger.warning(
                f"Position '{self.position}' depends on variables"
                f" {dependent_variables} and will be undefined until these variables"
                " are set"
            )
        else:
            extra[DeviceParameter("initial_position")] = self.position.evaluate(units)
        return super().get_device_init_args() | extra

    @classmethod
    def get_default_config(cls, device_name: str, remote_server: str) -> Self:
        return cls(
            device_name=device_name,
            remote_server=remote_server,
            serial_port="COM0",
            device_id=0,
            position=Expression("0"),
        )


YAMLSerializable.register_attrs_class(ElliptecELL14RotationStageConfiguration)
