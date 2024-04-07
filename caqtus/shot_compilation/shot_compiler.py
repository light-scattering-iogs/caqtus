from collections.abc import Mapping
from typing import Protocol, Any

from caqtus.device import DeviceName, DeviceConfiguration
from caqtus.session.shot import TimeLanes
from .compilation_contexts import ShotContext
from .variable_namespace import VariableNamespace


class ShotCompiler(Protocol):
    def __init__(
        self,
        shot_timelanes: TimeLanes,
        device_configurations: Mapping[DeviceName, DeviceConfiguration],
    ):
        self.shot_time_lanes = shot_timelanes
        self.device_configurations = device_configurations

    def compile_shot(
        self, shot_parameters: VariableNamespace
    ) -> Mapping[DeviceName, Mapping[str, Any]]:
        shot_context = ShotContext(self.shot_time_lanes, shot_parameters.dict())

        results = {}
        for device_name in self.device_configurations:
            results[device_name] = shot_context.get_shot_parameters(device_name)

        return results


class ShotCompilerFactory(Protocol):
    """Creates shot compilers."""

    def __call__(
        self,
        shot_timelanes: TimeLanes,
        device_configurations: Mapping[DeviceName, DeviceConfiguration],
    ) -> ShotCompiler:
        """Create a shot compiler.

        The shot compiler returned by this function will be used to compile the shot
        represented by `shot_timelanes` using the device configurations in
        `device_configurations`.

        The keys of the mapping returned by the method :meth:`compile_shot` of the
        shot compiler created must be a subset of the keys of `device_configurations`.

        Args:
            shot_timelanes: The generic shot description to compile.
            device_configurations: The device configurations to use to compile the shot.
        """

        ...
