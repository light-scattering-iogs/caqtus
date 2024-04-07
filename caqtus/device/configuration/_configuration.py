"""This module contains the :class:`DeviceConfiguration` class."""

from __future__ import annotations

import abc
from collections.abc import Mapping
from typing import Any, TypeVar, Optional, NewType, Generic, ForwardRef, TYPE_CHECKING

import attrs

from caqtus.device.name import DeviceName
from caqtus.device.runtime import Device
from ._get_generic_map import get_generic_map

if TYPE_CHECKING:
    from caqtus.shot_compilation import SequenceContext, ShotContext

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

    @abc.abstractmethod
    def get_device_initialization_method(
        self, device_name: DeviceName, sequence_context: "SequenceContext"
    ) -> DeviceInitializationMethod:
        """Indicate how the device should be initialized.

        Args:
            device_name: The name of the device being initialized.
            sequence_context: Contains the information about the sequence being run.
        Raises:
            DeviceNotUsedException: If the device is not used in the current sequence.

        The base implementation of this method inspect the device type argument of the
        configuration to determine how the device should be initialized.
        """

        device_type = get_generic_map(DeviceConfiguration, type(self)).get(DeviceType)  # type: ignore

        if device_type is None:
            raise ValueError(
                f"Could not find the device type for configuration {self}."
            )

        if self.remote_server is None:
            if isinstance(device_type, ForwardRef):
                raise ValueError(
                    f"Can't resolve the device type {device_type} for"
                    f" device {device_name}."
                )
            elif issubclass(device_type, Device):
                return LocalProcessInitialization(
                    device_type=device_type,  # type: ignore
                    init_kwargs={},
                )
            else:
                raise ValueError(
                    f"The device type {device_type} is not a subclass of Device."
                )
        else:
            if isinstance(device_type, ForwardRef):
                device_type_name = device_type.__forward_arg__
            elif isinstance(device_type, str):
                device_type_name = device_type
            elif issubclass(device_type, Device):
                device_type_name = device_type.__name__
            else:
                raise ValueError(
                    f"The device type {device_type} is not a subclass of Device."
                )
            return RemoteProcessInitialization(
                server_name=self.remote_server,
                device_type=device_type_name,
                init_kwargs={},
            )

    @abc.abstractmethod
    def compile_device_shot_parameters(
        self,
        device_name: DeviceName,
        shot_context: "ShotContext",
    ) -> Mapping[str, Any]:
        """Compute the parameters that should be applied to the device for a shot.

        The parameters returned by this method will be passed to the method
        :meth:`DeviceController.run_shot` of the device controller.
        The keys in the return mapping must match the arguments of this method.

        Args:
            device_name: The name of the device for which the parameters are being
                compiled.
            shot_context: Contains the information about the shot being run.
        """

        raise NotImplementedError


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


class DeviceNotUsedException(Exception):
    """Raised when a device is not used in a sequence."""

    pass


@attrs.define
class LocalProcessInitialization:
    device_type: type[Device]
    init_kwargs: dict[str, Any]


@attrs.define
class RemoteProcessInitialization:
    server_name: DeviceServerName
    device_type: str
    init_kwargs: dict[str, Any]


DeviceInitializationMethod = LocalProcessInitialization | RemoteProcessInitialization
