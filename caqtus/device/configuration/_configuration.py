"""This module contains the :class:`DeviceConfiguration` class."""

from __future__ import annotations

from collections.abc import Mapping
from typing import (
    TypeVar,
    Optional,
    NewType,
    Generic,
)

import attrs

from caqtus.device import DeviceName
from caqtus.device.runtime import Device
from caqtus.shot_compilation import SequenceContext
from caqtus.types.data import DataType, DataLabel
from caqtus.utils.result import Success, Failure

DeviceServerName = NewType("DeviceServerName", str)

DeviceType = TypeVar("DeviceType", bound=Device)


@attrs.define
class DeviceConfiguration(Generic[DeviceType]):
    """Contains static information about a device.

    This is an abstract class, generic in :data:`DeviceType` that stores the information
    necessary to connect to a device and program it during a sequence.

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

    def get_data_schema(
        self, name: DeviceName, sequence_context: SequenceContext
    ) -> Success[Mapping[DataLabel, DataType]] | Failure[DataSchemaError]:
        return Success({})


class DataSchemaError(Exception):
    """An error occurred while trying to get the data schema."""


DeviceConfigType = TypeVar("DeviceConfigType", bound=DeviceConfiguration)
