import abc
import datetime
import uuid
from collections.abc import MutableMapping

from core.device import DeviceName, DeviceConfigurationAttrs


class DeviceConfigurationCollection(
    MutableMapping[DeviceName, DeviceConfigurationAttrs], abc.ABC
):
    """Gives access to the history of the device configurations."""

    def __len__(self):
        return len(self.get_in_use_uuids())

    def __iter__(self):
        in_use_uuids = self.get_in_use_uuids()
        configurations_uuids = {self.get_device_name(id_): id_ for id_ in in_use_uuids}
        return iter(configurations_uuids)

    def __getitem__(self, key):
        in_use_uuids = self.get_in_use_uuids()
        configurations_uuids = {self.get_device_name(id_): id_ for id_ in in_use_uuids}
        configuration_uuid = configurations_uuids[key]
        return self.get_configuration(configuration_uuid)

    def __setitem__(self, key, value):
        id_ = self.add_device_configuration(key, value)
        self.set_in_use(id_)

    def __delitem__(self, key):
        in_use_uuids = self.get_in_use_uuids()
        configurations_uuids = {self.get_device_name(id_): id_ for id_ in in_use_uuids}
        configuration_uuid = configurations_uuids[key]
        self.remove_from_use(configuration_uuid)

    @abc.abstractmethod
    def get_device_name(self, id_: uuid.UUID) -> DeviceName:
        """Get the name of the device configuration with the given id."""

        ...

    @abc.abstractmethod
    def get_configuration(self, id_: uuid.UUID) -> DeviceConfigurationAttrs:
        """Get the device configuration with the given UUID."""

        ...

    @abc.abstractmethod
    def add_device_configuration(
        self,
        device_name: DeviceName,
        device_configuration: DeviceConfigurationAttrs,
    ) -> uuid.UUID:
        """Add a new device configuration to the session.

        Args:
            device_configuration: the device configuration to add to the session.
            device_name: the name of the device to which the configuration belongs.

        Returns:
            The UUID of the device configuration.
        """

        ...

    @abc.abstractmethod
    def set_in_use(self, id_: uuid.UUID) -> None:
        """Set the device configuration to be in use.

        If another device configuration with the same device name is already in use, it
        will be replaced by this one.
        """

        ...

    @abc.abstractmethod
    def remove_from_use(self, id_: uuid.UUID) -> None:
        """Remove the device configuration from the in use configurations."""

        ...

    @abc.abstractmethod
    def get_in_use_uuids(self) -> set[uuid.UUID]:
        """Get the device configurations that are in use."""

        ...

    @staticmethod
    def _create_uuid(device_name: DeviceName, date: datetime.datetime) -> uuid.UUID:
        return uuid.uuid5(uuid.NAMESPACE_DNS, f"{device_name}/{date}")
