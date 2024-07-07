"""This module contains the :class:`DeviceConfiguration` class."""

from __future__ import annotations

import abc
from collections.abc import Mapping
from typing import (
    TypeVar,
    Optional,
    NewType,
    Generic,
)

import attrs

from caqtus.device.name import DeviceName
from caqtus.device.runtime import Device

DeviceServerName = NewType("DeviceServerName", str)

DeviceType = TypeVar("DeviceType", bound=Device)


@attrs.define
class DeviceConfiguration(abc.ABC, Generic[DeviceType]):
    """Contains static information about a device.

    This is an abstract class, generic in :data:`DeviceType` that stores the information
    necessary to connect to a device and program it during a sequencer.

    This information is meant to be encoded in a user-friendly way that might not be
    possible to be directly programmed on a device.
    For example, it might contain not yet evaluated
    :class:`caqtus.types.expression.Expression` objects that only make sense in the
    context of a shot.

    Attributes:
        remote_server: Indicates the name of the computer on which the device should be
            instantiated.
            If None, the device should be instantiated in the local process controlling
            the experiment.
    """

    remote_server: Optional[DeviceServerName] = attrs.field(
        converter=attrs.converters.optional(str),
        on_setattr=attrs.setters.convert,
    )


DeviceConfigType = TypeVar("DeviceConfigType", bound=DeviceConfiguration)


def get_configurations_by_type(
    device_configurations: Mapping[DeviceName, DeviceConfiguration],
    device_type: type[DeviceConfigType],
) -> dict[DeviceName, DeviceConfigType]:
    return {
        name: configuration
        for name, configuration in device_configurations.items()
        if isinstance(configuration, device_type)
    }
