from abc import ABC, abstractmethod
from contextlib import ExitStack, AbstractContextManager
from typing import ClassVar, Optional, TypeVar

from attr import define, field
from attr.setters import frozen

from device.configuration import DeviceName

_T = TypeVar("_T")


@define(slots=False)
class RuntimeDevice(ABC, AbstractContextManager):
    """A class that is instantiated to directly control a physical device

    All devices used in the experiment must inherit from this class.
    Objects of this class can be used as context managers to automatically start and shutdown the device.

    Fields:
        name: A unique name given to the device. It is used to identify the device in the experiment configuration.

    Methods:
        __init__: The constructor of the class. It is used to initialize the device parameters. No communication
            to the device should be done here, it is only used to set the parameters.
        initialize: This method must be called once before attempting any communication with the actual device. It is
            used to initiate the communication to the device.
        update_parameters: This method is used to change the values of some parameters of the device. It can be called
            as many times as needed.
        close: This method must be called once when use of the device is finished. It is used to close the
            communication to the device and free the resources used by the device.

    Warnings:
        All device classes subclassed from this class should call parent_item class start and shutdown methods when
        subclassing them.
    """

    name: DeviceName = field(on_setattr=frozen)

    _close_stack: Optional[ExitStack] = field(init=False, default=None)
    __devices_already_in_use: ClassVar[dict[DeviceName, "RuntimeDevice"]] = {}

    @name.validator  # type: ignore
    def _validate_name(self, attribute, value):
        if not isinstance(value, str):
            raise TypeError(f"Expected DeviceName, got {type(value)}")

    @abstractmethod
    def initialize(self) -> None:
        """Initiate the communication to the device.

        This method is meant to be reimplemented for each specific device. The base class implementation registers the
        device in the list of devices already in use. It must be called when subclassing this class.
        """

        self._close_stack = ExitStack()

        if self.name in self.__devices_already_in_use:
            raise ValueError(f"A device with name {self.name} is already in use")
        self.__devices_already_in_use[self.name] = self
        self._add_closing_callback(self.__devices_already_in_use.pop, self.name)

    def _add_closing_callback(self, callback, /, *args, **kwargs):
        """Add a callback function to be called when the device is closed.

        Callbacks will be called in the reverse order they were added. The callback is called with the same arguments as
        passed to this method.
        """

        if self._close_stack is None:
            raise UninitializedDeviceError(
                f"Method RuntimeDevice.initialize must be called on the instance before adding shutdown callbacks."
            )
        self._close_stack.callback(callback, *args, **kwargs)

    def _enter_context(self, cm: AbstractContextManager[_T]) -> _T:
        """Enter a context manager to be closed when the device is closed."""

        if self._close_stack is None:
            raise UninitializedDeviceError(
                f"Method RuntimeDevice.initialize must be called on the instance before entering context managers."
            )
        return self._close_stack.enter_context(cm)

    @abstractmethod
    def update_parameters(self, *_, **kwargs) -> None:
        """Apply new values for some parameters of the device.

        This method is meant to be reimplemented for each specific device. It can be called as many times as needed. The
        base class implementation updates the device attributes with the new values passed as keyword arguments.
        """

        for name, value in kwargs.items():
            setattr(self, name, value)

    def close(self) -> None:
        """Close the communication to the device and free the resources used by the device.

        This method must be called once when use of the device is finished. The base class implementation unwinds the
        stack of closing callbacks.
        """

        if self._close_stack is None:
            raise UninitializedDeviceError(
                f"method initialize of RuntimeDevice must be called before calling close."
            )
        self._close_stack.close()
        self._close_stack = None

    def __enter__(self):
        try:
            self.initialize()
        except Exception:
            self.close()
            raise
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_name(self) -> DeviceName:
        return self.name

    @classmethod
    def exposed_remote_methods(cls) -> tuple[str, ...]:
        return "initialize", "update_parameters", "close", "get_name"


class UninitializedDeviceError(Exception):
    """Raised when a device is used before being initialized"""

    pass
