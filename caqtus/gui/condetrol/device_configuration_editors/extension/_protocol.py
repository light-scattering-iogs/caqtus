from typing import Protocol, TypeVar

from caqtus.device import DeviceConfiguration
from .._device_configuration_editor import DeviceConfigurationEditor

C = TypeVar("C", bound=DeviceConfiguration)


class CondetrolDeviceExtensionProtocol(Protocol):
    """Defines the operations necessary to extend Condetrol with new device."""

    def get_device_configuration_editor(
        self, device_configuration: C
    ) -> DeviceConfigurationEditor[C]:
        """Create an editor for the given device configuration.

        This method is called when the user wants to edit a device configuration.
        The returned editor will be used to display and modify the device configuration.
        """

        ...

    def available_new_configurations(self) -> set[str]:
        """Return the new configurations that can be created.

        This method is called when the user wants to create a new device configuration.
        The user will be able to choose one of the returned labels.
        """

        ...

    def create_new_device_configuration(
        self, configuration_label: str
    ) -> DeviceConfiguration:
        """Create a new device configuration.

        This method is called when the user wants to create a new device configuration.
        The label of the configuration to create is passed as an argument.
        """

        ...
