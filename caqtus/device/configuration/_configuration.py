"""This module contains the :class:`DeviceConfiguration` class."""

from __future__ import annotations

import abc
from typing import (
    TypeVar,
    NewType,
)

import attrs

DeviceServerName = NewType("DeviceServerName", str)


@attrs.define(eq=False)
class DeviceConfiguration:
    """Contains static information about a device.

    This is an abstract class, generic in :data:`DeviceType` that stores the information
    necessary to connect to a device and program it during a sequence.

    This information is meant to be encoded in a user-friendly way that might not be
    possible to be directly programmed on a device.
    For example, it might contain not yet evaluated
    :class:`caqtus.types.expression.Expression` objects that only make sense in the
    context of a shot.

    Subclasses should add necessary attributes depending on the device.

    The dunder method :meth:`__eq__` must be implemented.
    """

    @abc.abstractmethod
    def __eq__(self, other):
        raise NotImplementedError


DeviceConfigType = TypeVar("DeviceConfigType", bound=DeviceConfiguration)
