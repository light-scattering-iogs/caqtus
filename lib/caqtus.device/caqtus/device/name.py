from typing import NewType, TypeGuard

DeviceName = NewType("DeviceName", str)


def is_device_name(name: str) -> TypeGuard[DeviceName]:
    return isinstance(name, str) and len(name) > 0
