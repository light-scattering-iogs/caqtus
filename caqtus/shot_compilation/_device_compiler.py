from __future__ import annotations

import abc
from collections.abc import Mapping
from typing import Protocol, Any

from caqtus.device import DeviceName, DeviceParameter
from .compilation_contexts import SequenceContext, ShotContext


class DeviceCompiler(Protocol):
    """Defines the interface for a device compiler.

    Each device compiler is responsible to evaluate the parameters to apply to a device.

    Its role is to translate high-level and user-friendly parameters into concrete
    low-level device parameters that can be used to program the device.

    The compiler is initialized at the beginning of a sequence.
    Its method :meth:`compile_initialization_parameters` is then called once to
    obtain the parameters to pass to the device constructor.

    The for each shot, the method :meth:`compile_shot_parameters` is called to pass to
    the device controller for this shot.
    """

    @abc.abstractmethod
    def __init__(self, device_name: DeviceName, sequence_context: SequenceContext):
        """Initialize the device compiler.

        Args:
            device_name: The name of the device for which the compiler is being created.
                The device name can be used to retrieve the device configuration in the
                sequence context.
            sequence_context: The context of the sequence being compiled.
                It contains information about the current that can be useful to evaluate
                device parameters.
        Raises:
            DeviceNotUsedException: If the device is not used in the current sequence.
        """

        ...

    @abc.abstractmethod
    def compile_initialization_parameters(self) -> Mapping[DeviceParameter, Any]:
        """Compile the parameters to pass to the device constructor."""

        ...

    @abc.abstractmethod
    def compile_shot_parameters(self, shot_context: ShotContext) -> Mapping[str, Any]:
        """Compile the parameters to pass to the device controller for a shot.

        Args:
            shot_context: The context of the shot being compiled.
                It contains information about the shot that can be useful to evaluate
                device parameters.
        """

        ...


class DeviceNotUsedException(Exception):
    """Raised when a device is not used in a sequence."""

    pass
