from typing import NewType, TypeGuard

DeviceName = NewType("DeviceName", str)
"""A non-empty string that uniquely identifies a device."""


def is_device_name(name: str) -> TypeGuard[DeviceName]:
    return isinstance(name, str) and len(name) > 0
