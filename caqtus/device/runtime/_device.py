import abc
from typing import runtime_checkable, Protocol, Self, ParamSpec

InitParams = ParamSpec("InitParams")


@runtime_checkable
class Device(Protocol[InitParams]):
    """Wraps a low-level instrument that can be controlled during an experiment.

    Subclasses of this class should at least implement the :meth:`__init__`,
    :meth:`__enter__`, and :meth:`__exit__` methods.
    In addition to these methods, any other methods that are specific to the device
    should be implemented.
    """

    @abc.abstractmethod
    def __init__(self, *args: InitParams.args, **kwargs: InitParams.kwargs) -> None:
        """Device constructor.

        No communication to an instrument or initialization should be done in the
        constructor.
        Instead, use the :meth:`__enter__` method to acquire the necessary resources.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def __enter__(self) -> Self:
        """Initialize the device.

        Used to establish communication to the device and allocate the necessary
        resources.

        Warnings:
            If you need to acquire multiple resources in the :meth:`__enter__` method,
            you need to ensure that the first resources are correctly released if an
            error occurs while acquiring the subsequent resources.

            If this is the case, you can use this pattern: :ref:`clean-up-enter`.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Shutdown the device.

        Used to terminate communication to the device and free the associated resources.
        """

        raise NotImplementedError
