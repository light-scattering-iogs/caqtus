from __future__ import annotations

from collections.abc import Callable
from typing import Generic, TypeVar

import attrs

from caqtus.device import DeviceConfiguration
from caqtus.gui.condetrol.device_configuration_editors import DeviceConfigurationEditor
from caqtus.utils.serialization import JSON

_C = TypeVar("_C", bound=DeviceConfiguration)


@attrs.frozen
class DeviceExtension(Generic[_C]):
    """Extension to define how to implement a device in the application.

    This class is generic in the :class:`DeviceConfiguration` type.

    Attributes:
        label: A human-readable label for the type of device represented by this
            extension.
            This label will be displayed to the user when they are selecting a device
            to add to the experiment.
        configuration_type: The type of configuration used to store the settings of
            the device.
        configuration_factory: A factory function that returns a new instance of the
            configuration type.
            This function will be called when a new device of this type is added to the
            experiment.
            It should return a default instance of the configuration type.
        configuration_dumper: A function that converts a configuration instance to a
            JSON-serializable format.
            This function will be used to save the configuration.
        configuration_loader: A function that converts a JSON-serializable format to a
            configuration instance.
            This function will be used to load the configuration.
            It is passed the JSON-serializable format saved by the
            `configuration_dumper` function.
        editor_type: A function that returns an editor for the device configuration.
            When the user wants to edit the configuration of a device of this type,
            this function will be called to create an editor for the configuration.
            The method :meth:`DeviceConfiguration.get_configuration` of the editor will be
            called when the user validates the configuration.
    """

    label: str = attrs.field(converter=str)
    configuration_type: type[_C] = attrs.field()
    configuration_factory: Callable[[], _C] = attrs.field()
    configuration_dumper: Callable[[_C], JSON] = attrs.field()
    configuration_loader: Callable[[JSON], _C] = attrs.field()
    editor_type: Callable[[_C], DeviceConfigurationEditor[_C]] = attrs.field()

    @configuration_type.validator  # type: ignore
    def _validate_configuration_type(self, attribute, value):
        if not issubclass(value, DeviceConfiguration):
            raise ValueError(f"Invalid configuration type: {value}.")
