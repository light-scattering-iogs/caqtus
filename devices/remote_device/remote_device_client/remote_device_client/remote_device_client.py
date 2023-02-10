"""This module defines a client class that can be used to create and manage remote devices"""

from multiprocessing.managers import BaseManager


class RemoteDeviceClientManager(BaseManager):
    pass


# Client will only try to ask for the creation of a device type if it is registered

REGISTERED_DEVICE_TYPES: list[str] = [
    "OrcaQuestCamera",
    "SpincorePulseBlaster",
    "NI6738AnalogCard",
]

for device_type in REGISTERED_DEVICE_TYPES:
    RemoteDeviceClientManager.register(device_type)
