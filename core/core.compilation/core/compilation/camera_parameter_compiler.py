from collections.abc import Sequence, Mapping
from typing import TypedDict

from core.device import DeviceName
from core.device.camera import CameraConfiguration
from core.session.shot.timelane import CameraTimeLane
from core.types.expression import Expression
from .variable_namespace import VariableNamespace
from .lane_compilers import CameraLaneCompiler, evaluate_step_durations


class CameraParameters(TypedDict):
    timeout: float
    exposures: list[float]


class CamerasParameterCompiler:
    def __init__(
        self,
        step_names: Sequence[str],
        step_durations: Sequence[Expression],
        camera_lanes: Mapping[str, CameraTimeLane],
        camera_configurations: Mapping[DeviceName, CameraConfiguration],
    ):
        self.lane_compilers: dict[str, CameraLaneCompiler] = {}
        self.steps = list(zip(step_names, step_durations))
        for name, lane in camera_lanes.items():
            if name not in camera_configurations:
                raise ValueError(f"No camera device found for lane {name}")
            self.lane_compilers[name] = CameraLaneCompiler(
                lane, step_names, step_durations
            )

    def compile(
        self, variables: VariableNamespace
    ) -> dict[DeviceName, CameraParameters]:
        result = {}
        step_durations = evaluate_step_durations(self.steps, variables)
        shot_duration = sum(step_durations)
        for name, compiler in self.lane_compilers.items():
            result[DeviceName(name)] = CameraParameters(
                # Add 1 second to the shot duration, in case the shot takes a bit
                # longer than expected to start
                timeout=shot_duration + 1,
                exposures=compiler.compile_exposures(variables),
            )
        return result
