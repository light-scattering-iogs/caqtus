"""This module contains the :class:`DeviceConfiguration` class."""

import abc
from collections.abc import Mapping, Set
from typing import Any, TypeVar, Optional, NewType, Generic, ForwardRef, TYPE_CHECKING

import attrs

from caqtus.device.configuration._get_generic_map import get_generic_map
from caqtus.device.name import DeviceName
from caqtus.device.runtime import Device

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
    def get_device_init_args(self, *args, **kwargs) -> Mapping[str, Any]:
        """Return the arguments that should be passed to the device's constructor."""

        raise NotImplementedError

    def get_device_type(self) -> str:
        """Return the runtime type of the device.

        Return:
            A string containing the :data:`DeviceType` associated to this configuration.
            The default implementation of this method extracts the device type from the
            type variable :data:`DeviceType` associated to this configuration.
        """

        device_type = get_generic_map(DeviceConfiguration, type(self)).get(DeviceType)  # type: ignore

        if device_type is None:
            raise ValueError(
                f"Could not find the device type for configuration {self}."
            )

        if isinstance(device_type, ForwardRef):
            return device_type.__forward_arg__
        else:
            return device_type.__name__

    @abc.abstractmethod
    def compile_device_shot_parameters(
        self,
        sequence_context: SequenceContext,
        shot_context: ShotContext,
        already_compiled: Mapping[DeviceName, Mapping[str, Any]],
    ) -> Mapping[str, Any]:
        """Compute the parameters that should be applied to the device for a shot.

        The parameters returned by this method will be passed to the method
        :meth:`Device.update_parameters` of the related device before the shot is run.
        The keys in the return mapping must match the arguments of this method.

        Args:
            sequence_context: Contains the information about the sequence being run.
            shot_context: Contains the information about the shot being run.
            already_compiled: Contains the parameters of devices that have already been
                compiled for the current shot.
                If a device is listed by the current device's
                :meth:`shot_compilation_dependencies` and if this other device is
                being used in the current shot, its parameters will be available in this
                mapping.
        """

        raise NotImplementedError

    def shot_compilation_dependencies(self) -> Set[DeviceName]:
        """Return the devices whose parameters must be compiled before this device."""

        return set()


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
