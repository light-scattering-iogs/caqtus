import logging
from multiprocessing.managers import BaseManager, BaseProxy
from typing import Iterable

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
    def register_device(cls, device_type: type[Device]):
        cls.register(
            device_type.__name__,
            device_type,
            DeviceProxy,
        )
        cls.register("DeviceProxy", proxytype=DeviceProxy, create_method=False)


class DeviceProxy(BaseProxy, Device):
    _exposed_ = (
        "__enter__",
        "__exit__",
        "__repr__",
        "__str__",
        "get_name",
        "update_parameters",
    )
    _method_to_typeid_ = {"__enter__": "DeviceProxy"}

    def __enter__(self):
        return self._callmethod("__enter__")

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._callmethod("__exit__", (exc_type, exc_val, exc_tb))

    def __repr__(self) -> str:
        return f'DeviceProxy(name="{self.get_name()}")'

    def __str__(self) -> str:
        return self._callmethod("__str__")  # type: ignore

    def get_name(self) -> DeviceName:
        return self._callmethod("get_name")  # type: ignore
