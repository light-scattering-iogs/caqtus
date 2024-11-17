"""This module contains the :class:`DeviceConfiguration` class."""

from __future__ import annotations

import abc
from typing import (
    TypeVar,
    Optional,
    NewType,
)

import attrs

from caqtus.device.runtime import Device

DeviceServerName = NewType("DeviceServerName", str)

DeviceType = TypeVar("DeviceType", bound=Device)


@attrs.define
class DeviceConfiguration[DeviceType](abc.ABC):
    """Contains static information about a device.

    This is an abstract class, generic in :data:`DeviceType` that stores the information
    necessary to connect to a device and program it during a sequencer.

    This information is meant to be encoded in a user-friendly way that might not be
    possible to be directly programmed on a device.
    For example, it might contain not yet evaluated
    :class:`caqtus.types.expression.Expression` objects that only make sense in the
    context of a shot.

    Subclasses should add necessary attributes depending on the device.

    The dunder method :meth:`__eq__` should be implemented.

    Attributes:
        remote_server: Indicates the name of the computer on which the device should be
            instantiated.
    """

    remote_server: Optional[DeviceServerName] = attrs.field()


DeviceConfigType = TypeVar("DeviceConfigType", bound=DeviceConfiguration)
