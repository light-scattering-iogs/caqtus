import copy
from abc import abstractmethod
from typing import Generic, TypeVar, Collection

from PyQt6.QtWidgets import QWidget

from device.configuration import DeviceConfiguration
from device_server.name import DeviceServerName
from qabc import QABC

_T = TypeVar("_T", bound=DeviceConfiguration)


class ConfigEditor(QWidget, QABC, Generic[_T]):
    """An abstract interface defining how a widget should edit a device configuration."""

    def __init__(
        self,
        device_config: _T,
        available_remote_servers: Collection[DeviceServerName],
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._device_config = device_config
        self._available_remote_servers = available_remote_servers

    @abstractmethod
    def get_device_config(self) -> _T:
        """Return a copy of the device config currently shown in the UI."""
        return copy.deepcopy(self._device_config)
