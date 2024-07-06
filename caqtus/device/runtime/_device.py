import abc
from typing import runtime_checkable, Protocol, Self, ParamSpec

from ..name import DeviceName

UpdateParams = ParamSpec("UpdateParams")
InitParams = ParamSpec("InitParams")


@runtime_checkable
class Device(Protocol[InitParams, UpdateParams]):
    """Wraps a low-level instrument that can be controlled during an experiment.

    This abstract class defines the necessary methods that a device must implement to be
    used in an experiment.
    """

    @abc.abstractmethod
    def __init__(self, *args: InitParams.args, **kwargs: InitParams.kwargs) -> None:
        """Device constructor.

        No communication to an instrument or initialization should be done in the
        constructor.
        Instead, use the :meth:`__enter__` method to acquire the necessary resources.
        """

        raise NotImplementedError

    def get_name(self) -> DeviceName:
        """A unique name given to the device.

        It is used to identify the device in the experiment.
        This name must remain constant during the lifetime of the device.
        """

        ...

    def __str__(self) -> str:
        return self.get_name()

    @abc.abstractmethod
    def __enter__(self) -> Self:
        """Initialize the device.

        Used to establish communication to the device and allocate the necessary
        resources.

        Warnings:
            If you need to acquire multiple resources in the :meth:`__enter__` method,
            you need to ensure that the first resources are correctly released if an
            error occurs while acquiring the subsequent resources.

            In the following example, if `acquire_resource2()` raises an exception in
            the `__enter__` method, the `__exit__` method will not be called, and
            `self._resource1` will not be closed.
            A similar issue occurs if `resource2.close()` raises an exception, in which
            case `resource1.close()` will not be called.

            .. code-block:: python

                class MyDevice(Device):

                    def __enter__(self) -> Self:
                        self._resource1 = acquire_resource1()
                        self._resource2 = acquire_resource2()
                        return self

                    def __exit__(self, exc_type, exc_val, exc_tb):
                        self._resource2.close()
                        self._resource1.close()

            To avoid this issue, you can use a :class:`contextlib.ExitStack` .

            .. code-block:: python

                class MyDevice(Device):

                    def __enter__(self) -> Self:
                        self._stack = contextlib.ExitStack()

                        try:
                            self._resource1 = acquire_resource1()
                            self._stack.callback(resource1.close)
                            self._resource2 = acquire_resource2()
                            self._stack.callback(resource2.close)
                        except:
                            self._stack.close()
                            raise

                    def __exit__(self, exc_type, exc_val, exc_tb):
                        self._stack.close()
        """

        raise NotImplementedError

    def update_parameters(
        self, *args: UpdateParams.args, **kwargs: UpdateParams.kwargs
    ) -> None:
        """Apply new values for some parameters of the device."""

        ...

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Shutdown the device.

        Used to terminate communication to the device and free the associated resources.
        """

        raise NotImplementedError
