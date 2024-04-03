from collections.abc import Callable
from typing import Generic, TypeVar

import attrs
from caqtus.device import DeviceConfiguration
from caqtus.utils.serialization import JSON

T = TypeVar("T", bound=DeviceConfiguration)


@attrs.define
class DeviceConfigurationSerializer(Generic[T]):
    """Indicates how to serialize and deserialize device configurations."""

    dumper: Callable[[T], JSON]
    loader: Callable[[JSON], T]
