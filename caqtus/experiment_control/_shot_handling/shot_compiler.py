from collections.abc import Mapping
from typing import Any

from caqtus.device import DeviceName, DeviceConfiguration
from caqtus.session.shot import TimeLanes
from caqtus.shot_compilation import DeviceCompiler
from caqtus.shot_compilation.compilation_contexts import ShotContext, SequenceContext
from caqtus.shot_compilation.variable_namespace import VariableNamespace


class ShotCompiler:
    def __init__(
        self,
        shot_timelanes: TimeLanes,
        device_configurations: Mapping[DeviceName, DeviceConfiguration],
        device_compilers: Mapping[DeviceName, DeviceCompiler],
    ):
        self.shot_time_lanes = shot_timelanes
        self.device_configurations = device_configurations
        self._sequence_context = SequenceContext(
            device_configurations=device_configurations, time_lanes=shot_timelanes
        )
        self.device_compilers = device_compilers

    def compile_shot(
        self, shot_parameters: VariableNamespace
    ) -> tuple[Mapping[DeviceName, Mapping[str, Any]], float]:
        shot_context = ShotContext(
            sequence_context=self._sequence_context,
            variables=shot_parameters.dict(),
            device_compilers=self.device_compilers,
        )

        results = {}
        for device_name, compiler in self.device_compilers.items():
            results[device_name] = shot_context.get_shot_parameters(device_name)

        # noinspection PyProtectedMember
        if unused_lanes := shot_context._unused_lanes():
            raise ValueError(
                "The following lanes where not used during the shot: "
                + ", ".join(unused_lanes)
            )

        return results, shot_context.get_shot_duration()
