"""This module contains the :class:`DeviceConfiguration` class."""

from __future__ import annotations

import abc
from collections.abc import Mapping
from typing import (
    Any,
    TypeVar,
    Optional,
    NewType,
    Generic,
    Self,
)

import attrs

from caqtus.device.name import DeviceName
from caqtus.device.runtime import Device

DeviceServerName = NewType("DeviceServerName", str)

DeviceType = TypeVar("DeviceType", bound=Device)


@attrs.define
class DeviceConfiguration(abc.ABC, Generic[DeviceType]):
    """Maps from user-level configuration of a device to low-level device parameters.

    This is an abstract class, generic in :data:`DeviceType` that contains all the
    information necessary to run a device of type :data:`DeviceType`.

    Typically, this class hold the information that is necessary to instantiate a
    device and the information necessary to update the device's state during a shot.

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


@attrs.define
class LocalProcessInitialization:
    device_type: type[Device]
    init_kwargs: dict[str, Any]

    def with_extra_parameters(self, **kwargs) -> Self:
        self.init_kwargs.update(kwargs)
        return self


@attrs.define
class RemoteProcessInitialization:
    server_name: DeviceServerName
    device_type: str
    init_kwargs: dict[str, Any]

    def with_extra_parameters(self, **kwargs) -> Self:
        self.init_kwargs.update(kwargs)
        return self


DeviceInitializationMethod = LocalProcessInitialization | RemoteProcessInitialization
