from typing import runtime_checkable, Protocol, Self, ParamSpec

from ..name import DeviceName
from ...types.data import Data, DataLabel

P = ParamSpec("P")


@runtime_checkable
class Device(Protocol[P]):
    """Wraps a low-level instrument that can be controlled during an experiment.

    This abstract class defines the necessary methods that a device must implement to be
    used in an experiment.



    """

    def get_name(self) -> DeviceName:
        """A unique name given to the device.

        It is used to identify the device in the experiment.
        This name must remain constant during the lifetime of the device.
        """

        ...

    def __str__(self) -> str:
        return self.get_name()

    def __enter__(self) -> Self:
        """Initialize the device.

        Used to establish communication to the device and allocate the necessary
        resources.
        No initialization should be done in the constructor.
        """

        ...

    def update_parameters(self, *args: P.args, **kwargs: P.kwargs) -> None:
        """Apply new values for some parameters of the device."""

        ...

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Shutdown the device.

        Used to terminate communication to the device and free the associated resources.
        """

        ...


@runtime_checkable
class AcquisitionDevice(Protocol):
    """Defines the interface that a device must satisfy to provide data."""

    def get_data(self) -> dict[DataLabel, Data]:
        """Return the data produced by the device."""

        ...
