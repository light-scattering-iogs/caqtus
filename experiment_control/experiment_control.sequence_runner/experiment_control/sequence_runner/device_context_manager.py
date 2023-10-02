import contextlib
import logging

from device.runtime import RuntimeDevice

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class DeviceContextManager(contextlib.AbstractContextManager[RuntimeDevice]):
    """Wraps a device in context manager that closes the device when exiting the context.

    The only goal of this context manager is to provide better message on error."""

    def __init__(self, device: RuntimeDevice):
        self._device = device

    def __enter__(self) -> RuntimeDevice:
        return self._device

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self):
        # noinspection PyBroadException
        try:
            self._device.close()
            logger.debug(f"Device '{self._device.get_name()}' shut down.")
        except Exception:
            logger.error(
                f"An error occurred while closing '{self._device.get_name()}'",
                exc_info=True,
            )
