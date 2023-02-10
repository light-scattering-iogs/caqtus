import logging
import os
from multiprocessing.managers import BaseManager
from typing import Type

from device import RuntimeDevice

imported_devices: dict[str, Type[RuntimeDevice]] = {}

try:
    from orca_quest.runtime import OrcaQuestCamera

    imported_devices["OrcaQuestCamera"] = OrcaQuestCamera
except Exception:
    pass

try:
    from spincore_sequencer.runtime import SpincorePulseBlaster

    imported_devices["SpincorePulseBlaster"] = SpincorePulseBlaster
except Exception:
    pass

try:
    from ni6738_analog_card.runtime import NI6738AnalogCard

    imported_devices["NI6738AnalogCard"] = NI6738AnalogCard
except Exception:
    pass

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class RemoteDeviceServerManager(BaseManager):
    pass


for type_name, device_type in imported_devices.items():
    RemoteDeviceServerManager.register(
        type_name, device_type, exposed=device_type.exposed_remote_methods()
    )

password = os.environ.get("CAQTUS_DEVICE_SERVER_PASSWORD", None)
if password is None:
    raise ValueError(
        "The environment variable 'CAQTUS_DEVICE_SERVER_PASSWORD' is not set to any value"
    )

manager = RemoteDeviceServerManager(
    address=("", 65000), authkey=bytes(password, encoding="utf-8")
)
server = manager.get_server()
print(f"Server instantiated at {server.address}")
server.serve_forever()
