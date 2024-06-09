from __future__ import annotations

import logging
from multiprocessing.managers import BaseManager, BaseProxy
from typing import Iterable

from tblib import pickling_support

from caqtus.device.camera import Camera
from caqtus.device.sequencer import Sequencer, Trigger
from caqtus.types.image import Image
from .. import DeviceName
from ..runtime import Device

pickling_support.install()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def create_device_in_other_process(
    type_name: str, device_type: type[Device], exposed: Iterable[str]
):
    def inner(*args, **kwargs):
        manager = BaseManager()
        manager.register(type_name, device_type, exposed=list(exposed))
        manager.start()
        return getattr(manager, type_name)(*args, **kwargs)

    return inner


class DeviceProxy(BaseProxy, Device):
    """Proxy for a device running in a different process.

    Proxies of this type expose the methods defined in the :class:`Device` interface.
    It means that if you have a proxy of this type, you can use it like a regular
    device, and it will relay the calls to the underlying device running in a different
    process.
    If you want to expose more methods, you should create a new class that inherits from
    this one and add the methods you want to expose.
    """

    _exposed_: tuple[str, ...] = (
        "__enter__",
        "__exit__",
        "__repr__",
        "__str__",
        "get_name",
        "update_parameters",
    )
    _method_to_typeid_ = {"__enter__": __name__}

    def get_name(self) -> DeviceName:
        return self._callmethod("get_name")  # type: ignore

    def __enter__(self):
        return self._callmethod("__enter__")

    def update_parameters(self, *args, **kwargs):
        return self._callmethod("update_parameters", args, kwargs)

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._callmethod("__exit__", (exc_type, exc_val, exc_tb))

    def __repr__(self) -> str:
        return f'{type(self).__name__}(name="{self.get_name()}")'

    def __str__(self) -> str:
        return self._callmethod("__str__")  # type: ignore


class SequencerProxy(DeviceProxy, Sequencer):
    """A proxy that exposes the methods of the :class:`Sequencer` interface."""

    _exposed_ = DeviceProxy._exposed_ + (
        "start_sequence",
        "has_sequence_finished",
        "wait_sequence_finished",
        "get_trigger",
    )
    _method_to_typeid_ = {
        **DeviceProxy._method_to_typeid_,
        "__enter__": __name__,
    }

    def start_sequence(self) -> None:
        return self._callmethod("start_sequence")

    def has_sequence_finished(self) -> bool:
        return self._callmethod("has_sequence_finished")  # type: ignore

    def wait_sequence_finished(self) -> None:
        return self._callmethod("wait_sequence_finished")  # type: ignore

    def get_trigger(self) -> Trigger:
        return self._callmethod("get_trigger")  # type: ignore


class CameraProxy(DeviceProxy, Camera):
    """A proxy that exposes the methods of the :class:`Camera` interface."""

    _exposed_ = DeviceProxy._exposed_ + (
        "_start_acquisition",
        "_read_image",
        "_stop_acquisition",
    )
    _method_to_typeid_ = {
        **DeviceProxy._method_to_typeid_,
        "__enter__": __name__,
    }

    def _start_acquisition(self, exposures: list[float]) -> None:
        return self._callmethod("_start_acquisition", (exposures,))

    def _read_image(self, exposure: float) -> Image:
        return self._callmethod("_read_image", (exposure,))  # type: ignore

    def _stop_acquisition(self) -> None:
        return self._callmethod("_stop_acquisition")
