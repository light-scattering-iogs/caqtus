from __future__ import annotations

import logging
from multiprocessing.managers import BaseManager, BaseProxy
from typing import Iterable

from core.device.camera import Camera
from core.device.sequencer import Sequencer
from tblib import pickling_support

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


class RemoteDeviceServer:
    def __init__(self, address: tuple[str, int], authkey: bytes):
        self._address = address
        self._authkey = authkey
        self._remote_device_manager_class: BaseManager = type("RemoteDeviceManager", (BaseManager,), {})  # type: ignore

    def register(
        self, type_name: str, device_type: type[Device], exposed: Iterable[str]
    ):
        self._remote_device_manager_class.register(
            type_name,
            create_device_in_other_process(type_name, device_type, exposed),
        )

    def serve_forever(self):
        manager = self._remote_device_manager_class(
            address=self._address, authkey=self._authkey
        )
        server = manager.get_server()
        logger.info("Remote device server started")
        server.serve_forever()


class RemoteDeviceManager(BaseManager):
    @classmethod
    def register_device(cls, device_type: type[Device], proxy_type: type[DeviceProxy]):
        cls.register(
            device_type.__name__,
            device_type,
            proxy_type,
        )
        cls.register(
            proxy_type._method_to_typeid_["__enter__"],
            proxytype=proxy_type,
            create_method=False,
        )


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
        "initialize",
        "close",
    )
    _method_to_typeid_ = {"__enter__": __name__}

    def initialize(self) -> None:
        return self._callmethod("initialize")

    def close(self) -> None:
        return self._callmethod("close")
    def get_name(self) -> DeviceName:
        return self._callmethod("get_name")  # type: ignore

    def __enter__(self):
        return self._callmethod("__enter__")

    def update_parameters(self, *args, **kwargs):
        return self._callmethod("update_parameters", args, kwargs)

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._callmethod("__exit__", (exc_type, exc_val, exc_tb))

    def __repr__(self) -> str:
        return f'DeviceProxy(name="{self.get_name()}")'

    def __str__(self) -> str:
        return self._callmethod("__str__")  # type: ignore


class SequencerProxy(DeviceProxy, Sequencer):
    """A proxy that exposes the methods of the :class:`Sequencer` interface."""

    _exposed_ = DeviceProxy._exposed_ + (
        "start_sequence",
        "has_sequence_finished",
        "initialize",
        "close",
    )
    _method_to_typeid_ = {
        **DeviceProxy._method_to_typeid_,
        "__enter__": __name__,
    }

    def start_sequence(self) -> None:
        return self._callmethod("start_sequence")

    def has_sequence_finished(self) -> bool:
        return self._callmethod("has_sequence_finished")  # type: ignore

    def initialize(self) -> None:
        return self._callmethod("initialize")

    def close(self) -> None:
        return self._callmethod("close")


class CameraProxy(DeviceProxy, Camera):
    """A proxy that exposes the methods of the :class:`Camera` interface."""

    _exposed_ = DeviceProxy._exposed_ + (
        "_is_acquisition_in_progress",
        "_stop_acquisition",
        "_start_acquisition",
        "initialize",
        "close",
    )
    _method_to_typeid_ = {
        **DeviceProxy._method_to_typeid_,
        "__enter__": __name__,
    }

    def _is_acquisition_in_progress(self) -> bool:
        return self._callmethod("_is_acquisition_in_progress")  # type: ignore

    def _stop_acquisition(self):
        return self._callmethod("_stop_acquisition")

    def _start_acquisition(self, number_pictures: int):
        return self._callmethod("_start_acquisition", (number_pictures,))

    def initialize(self) -> None:
        return self._callmethod("initialize")

    def close(self) -> None:
        return self._callmethod("close")
