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
        shot_context = ShotContext(
            time_lanes=self.shot_time_lanes,
            variables=shot_parameters.dict(),
            device_configurations=self.device_configurations,
        )

        results = {}
        for device_name in self.device_configurations:
            results[device_name] = shot_context.get_shot_parameters(device_name)

        # noinspection PyProtectedMember
        if unused_lanes := shot_context._unused_lanes():
            raise ValueError(
                "The following lanes where not used during the shot: "
                + ", ".join(unused_lanes)
            )

        return results
