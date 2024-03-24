from typing import runtime_checkable, Protocol, Self

from ..name import DeviceName


@runtime_checkable
class Device(Protocol):
    """Defines the interface that a device must satisfy.

    This is a runtime checkable protocol so that we can test at runtime is an object has
    all the required methods and implement this interface, even if it not a direct
    subclass of Device.
    """

    def get_name(self) -> DeviceName:
        """A unique name given to the device.

        It is used to identify the device in the experiment.
        This name must remain constant during the lifetime of the device.
        """

    def __str__(self) -> str:
        return self.get_name()

    def __enter__(self) -> Self:
        """Initiate the communication to the device.

        Starts the device and acquire the necessary resources.
        """

        ...

    def update_parameters(self, *_, **kwargs) -> None:
        """Apply new values for some parameters of the device.

        This method is meant to be reimplemented for each specific device.
        It can be called as many times as needed.
        """

        ...

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Shutdown the device.

        Used to terminate communication to the device and free the associated resources.
        """

        ...
