import logging
from multiprocessing.managers import BaseManager
from typing import Type, Iterable

from device.runtime import RuntimeDevice

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class RemoteDeviceServer:
    def __init__(self, address: tuple[str, int], authkey: bytes):
        self._address = address
        self._authkey = authkey
        self._remote_device_manager_class: BaseManager = type("RemoteDeviceManager", (BaseManager,), {})  # type: ignore

    def register(
        self, type_name: str, device_type: Type[RuntimeDevice], exposed: Iterable[str]
    ):
        self._remote_device_manager_class.register(
            type_name, device_type, exposed=list(exposed)
        )

    def serve_forever(self):
        manager = self._remote_device_manager_class(
            address=self._address, authkey=self._authkey
        )
        server = manager.get_server()
        logger.info("Remote device server started")
        server.serve_forever()
