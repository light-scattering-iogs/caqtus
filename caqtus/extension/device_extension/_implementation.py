from collections.abc import Callable
from typing import Generic, TypeVar

import attrs

from caqtus.device import DeviceConfiguration
from caqtus.gui.condetrol.device_configuration_editors import DeviceConfigurationEditor

C = TypeVar("C", bound=DeviceConfiguration)


@attrs.frozen
class DeviceExtension(Generic[C]):
    label: str = attrs.field(converter=str)
    configuration_type: type[C] = attrs.field()
    configuration_factory: Callable[[], C] = attrs.field()
    editor_type: Callable[[C], DeviceConfigurationEditor[C]] = attrs.field()

    @configuration_type.validator  # type: ignore
    def _validate_configuration_type(self, attribute, value):
        if not issubclass(value, DeviceConfiguration):
            raise ValueError(f"Invalid configuration type: {value}.")
