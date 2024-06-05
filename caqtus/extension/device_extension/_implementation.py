from __future__ import annotations

from collections.abc import Callable
from typing import Generic

import attrs

from caqtus.device import DeviceConfiguration, Device

# noinspection PyPep8Naming
from caqtus.device.configuration import DeviceConfigType as C
from caqtus.device.controller import DeviceController
from caqtus.device.remote import DeviceProxy
from caqtus.gui.condetrol.device_configuration_editors import DeviceConfigurationEditor
from caqtus.shot_compilation import DeviceCompiler
from caqtus.utils.serialization import JSON


@attrs.frozen
class DeviceExtension(Generic[C]):
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
            The method :meth:`DeviceConfiguration.get_configuration` of the editor will
            be called when the user validates the configuration.
    """

    label: str = attrs.field(converter=str)
    device_type: Callable[..., Device] = attrs.field()
    configuration_type: type[C] = attrs.field()
    configuration_factory: Callable[[], C] = attrs.field()
    configuration_dumper: Callable[[C], JSON] = attrs.field()
    configuration_loader: Callable[[JSON], C] = attrs.field()
    editor_type: Callable[[C], DeviceConfigurationEditor[C]] = attrs.field()
    compiler_type: type[DeviceCompiler] = attrs.field()
    controller_type: type[DeviceController] = attrs.field()
    proxy_type: type[DeviceProxy] = attrs.field()

    @configuration_type.validator  # type: ignore
    def _validate_configuration_type(self, _, value):
        if not issubclass(value, DeviceConfiguration):
            raise ValueError(f"Invalid configuration type: {value}.")

    @compiler_type.validator  # type: ignore
    def _validate_compiler_type(self, _, value):
        if not issubclass(value, DeviceCompiler):
            raise ValueError(f"Invalid compiler type: {value}.")

    @controller_type.validator  # type: ignore
    def _validate_controller_type(self, _, value):
        if not issubclass(value, DeviceController):
            raise ValueError(f"Invalid controller type: {value}.")

    @proxy_type.validator  # type: ignore
    def _validate_proxy_type(self, _, value):
        if not issubclass(value, DeviceProxy):
            raise ValueError(f"Invalid proxy type: {value}.")
