"""This package defines the interface for a widget that allows to edit the configuration of a device. Each device
configuration can be associated with such widget."""


import copy
from abc import abstractmethod
from typing import Generic, TypeVar, Collection

from PyQt6.QtWidgets import QWidget

from device.configuration import DeviceConfiguration
from device_server.name import DeviceServerName
from qabc import QABC

_T = TypeVar("_T", bound=DeviceConfiguration)


class ConfigEditor(QWidget, QABC, Generic[_T]):
    """An abstract interface defining how a widget should edit a device configuration.

    Implementations should specify the type of the device configuration they edit by setting the generic type
    parameter.
    """

    def __init__(
        self,
        device_config: _T,
        available_remote_servers: Collection[DeviceServerName],
        *args,
        **kwargs
    ):
        """Initialize the widget.

        Args:
            device_config: The device config to edit. The widget will make a copy of the object.
            available_remote_servers: The remote servers available to choose from for device_config.remote_server.
        """

        super().__init__(*args, **kwargs)
        self._device_config = copy.deepcopy(device_config)
        self._available_remote_servers = available_remote_servers

    @abstractmethod
    def get_device_config(self) -> _T:
        """Return a copy of the device config currently shown in the UI.

        This method is meant to be subclassed by the concrete implementation of the widget. The default implementation
        just returns a copy of the config passed to the constructor. An actual widget will rewrite some attributes of
        this config.
        """

        return copy.deepcopy(self._device_config)
