from abc import ABC, abstractmethod
from functools import singledispatchmethod
from typing import ClassVar, Self

import pydantic
from pydantic import Field, Extra

from .device_name import DeviceName


class RuntimeDevice(pydantic.BaseModel, ABC):
    """A class that is instantiated to directly control a physical device

    All devices used in the experiment must inherit from this class.
    Objects of this class can be used as context managers to automatically start and shutdown the device.

    Attributes:
        name: A unique name given to the device. It is used to identify the device in the experiment configuration.

    Methods:
        __init__: The constructor of the class. It is used to initialize the device parameters. No communication
            to the device should be done here, it is only used to set the parameters.
        start: This method must be called once before attempting any communication with the actual device. It is used to
            initiate the communication to the device.
        update_parameters: This method is used to change the values of some parameters of the device. It can be called
            as many times as needed.
        shutdown: This method must be called once when use of the device is finished. It is used to close the
            communication to the device and free the resources used by the device.

    Warnings:
        All device classes subclassed from this class should call parent_item class start and shutdown methods when
        subclassing them.
    """

    name: DeviceName = Field(allow_mutation=False)

    @abstractmethod
    def start(self) -> None:
        """Initiate the communication to the device.

        This method is meant to be reimplemented for each specific device.
        The base class implementation registers the device in the list of devices already in use. It should be called
        when subclassing this class.
        """

        if self.name in self._devices_already_in_use:
            raise ValueError(f"A device with name {self.name} is already in use")
        else:
            self._devices_already_in_use[self.name] = self

    @abstractmethod
    def update_parameters(self, **kwargs) -> None:
        """Apply new values for some parameters of the device.

        This method is meant to be reimplemented for each specific device. It can be called as many times as needed. The
        base class implementation updates the device attributes with the new values passed as keyword arguments.
        """

        for name, value in kwargs.items():
            setattr(self, name, value)

    @abstractmethod
    def shutdown(self) -> None:
        """Close the communication to the device and free the resources used by the device.

        This method is meant to be reimplemented for each specific device. It must be called once when use of the device
        is finished. The base class implementation unregisters the device from the list of devices in use.
        """

        del self._devices_already_in_use[self.name]

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

    @classmethod
    def exposed_remote_methods(cls) -> tuple[str, ...]:
        return "start", "update_parameters", "shutdown"

    class Config:
        validate_assignment = True
        use_enum_values = True
        validate_all = True
        keep_untouched = (singledispatchmethod,)
        arbitrary_types_allowed = True
        extra = Extra.allow

    _devices_already_in_use: ClassVar[dict[DeviceName, Self]] = {}
