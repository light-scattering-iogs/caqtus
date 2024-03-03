from collections.abc import Callable
from typing import Generic, TypeVar

import attrs
from core.device import DeviceConfigurationAttrs
from util.serialization import JSON

T = TypeVar("T", bound=DeviceConfigurationAttrs)


@attrs.define
class DeviceConfigurationSerializer(Generic[T]):
    """Indicates how to serialize and deserialize device configurations."""

    dumper: Callable[[T], JSON]
    loader: Callable[[JSON], T]
