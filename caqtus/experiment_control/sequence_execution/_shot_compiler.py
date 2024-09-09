from __future__ import annotations

import abc
from collections.abc import Mapping, Callable
from typing import Any
from typing import Protocol

import anyio.to_process

from caqtus.device import DeviceName, DeviceConfiguration
from caqtus.shot_compilation import (
    SequenceContext,
    DeviceCompiler,
    DeviceNotUsedException,
)
from caqtus.shot_compilation.compilation_contexts import ShotContext
from caqtus.shot_compilation.variable_namespace import VariableNamespace
from caqtus.types.recoverable_exceptions import InvalidValueError
from caqtus.types.timelane import TimeLanes
from ._shot_primitives import ShotParameters
from ..device_manager_extension import DeviceManagerExtensionProtocol


class ShotCompilerProtocol(Protocol):
    @abc.abstractmethod
    def compile_initialization_parameters(
        self,
    ) -> Mapping[DeviceName, Mapping[str, Any]]:
        """Compile the initialization parameters for the devices.

        Returns:
            A mapping from device names to the initialization parameters for each
            device.

            The keys of the mapping are the device names that are in use for this
            sequence.
        """

        raise NotImplementedError

    @abc.abstractmethod
    async def compile_shot(
        self, shot_parameters: ShotParameters
    ) -> tuple[Mapping[DeviceName, Mapping[str, Any]], float]:
        raise NotImplementedError


type ShotCompilerFactory = Callable[
    [SequenceContext, DeviceManagerExtensionProtocol], ShotCompilerProtocol
]


class ShotCompiler(ShotCompilerProtocol):
    def __init__(
        self,
        shot_timelanes: TimeLanes,
        device_configurations: Mapping[DeviceName, DeviceConfiguration],
        device_compilers: Mapping[DeviceName, DeviceCompiler],
    ):
        self.shot_time_lanes = shot_timelanes
        self.device_configurations = device_configurations
        self._sequence_context = SequenceContext(
            device_configurations=device_configurations,  # pyright: ignore[reportCallIssue]
            time_lanes=shot_timelanes,  # pyright: ignore[reportCallIssue]
        )
        self.device_compilers = device_compilers

    def compile_initialization_parameters(
        self,
    ) -> Mapping[DeviceName, Mapping[str, Any]]:
        initialization_parameters = {}
        for device_name, compiler in self.device_compilers.items():
            initialization_parameters[device_name] = (
                compiler.compile_initialization_parameters()
            )
        return initialization_parameters

    async def compile_shot(
        self, shot_parameters: ShotParameters
    ) -> tuple[Mapping[DeviceName, Mapping[str, Any]], float]:
        return await anyio.to_process.run_sync(
            self.compile_shot_sync, shot_parameters.parameters
        )

    def compile_shot_sync(
        self, shot_parameters: VariableNamespace
    ) -> tuple[Mapping[DeviceName, Mapping[str, Any]], float]:
        shot_context = ShotContext(
            sequence_context=self._sequence_context,  # pyright: ignore[reportCallIssue]
            variables=shot_parameters.dict(),  # pyright: ignore[reportCallIssue]
            device_compilers=self.device_compilers,  # pyright: ignore[reportCallIssue]
        )

        results = {}
        for device_name in self.device_compilers:
            results[device_name] = shot_context.get_shot_parameters(device_name)

        # noinspection PyProtectedMember
        if unused_lanes := shot_context._unused_lanes():
            raise InvalidValueError(
                "The following lanes where not used during the shot: "
                + ", ".join(unused_lanes)
            )

        return results, float(shot_context.get_shot_duration())


def create_shot_compiler(
    initial_sequence_context: SequenceContext,
    device_manager_extension: DeviceManagerExtensionProtocol,
) -> ShotCompiler:
    device_compilers = create_device_compilers(
        initial_sequence_context, device_manager_extension
    )
    in_use_configurations = {
        device_name: initial_sequence_context.get_device_configuration(device_name)
        for device_name in device_compilers
    }
    shot_compiler = _create_shot_compiler(
        time_lanes=initial_sequence_context._time_lanes,  # noqa
        device_configurations=in_use_configurations,
        device_compilers=device_compilers,
    )
    return shot_compiler


def create_device_compilers(
    sequence_context: SequenceContext,
    device_manager_extension: DeviceManagerExtensionProtocol,
) -> dict[DeviceName, DeviceCompiler]:
    device_compilers = {}
    for (
        device_name,
        device_configuration,
    ) in sequence_context.get_all_device_configurations().items():
        compiler_type = device_manager_extension.get_device_compiler_type(
            device_configuration
        )
        try:
            compiler = compiler_type(device_name, sequence_context)
        except DeviceNotUsedException:
            continue
        else:
            device_compilers[device_name] = compiler
    return device_compilers


def _create_shot_compiler(
    time_lanes: TimeLanes,
    device_configurations: Mapping[DeviceName, DeviceConfiguration],
    device_compilers: Mapping[DeviceName, DeviceCompiler],
) -> ShotCompiler:
    shot_compiler = ShotCompiler(
        time_lanes,
        device_configurations=device_configurations,
        device_compilers=device_compilers,
    )
    return shot_compiler
