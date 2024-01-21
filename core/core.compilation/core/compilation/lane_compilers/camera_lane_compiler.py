from collections.abc import Sequence
from typing import assert_never

import numpy as np

from core.device.sequencer.instructions import SequencerInstruction, Pattern, join
from core.session.shot.timelane.camera_time_lane import CameraTimeLane, TakePicture
from core.types.expression import Expression
from .evaluate_step_durations import evaluate_step_durations
from .timing import get_step_bounds, number_ticks, ns
from ..variable_namespace import VariableNamespace


class CameraLaneCompiler:
    def __init__(
        self,
        lane: CameraTimeLane,
        step_names: Sequence[str],
        step_durations: Sequence[Expression],
    ):
        if len(lane) != len(step_names):
            raise ValueError(
                f"Number of steps in lane ({len(lane)}) does not match number of"
                f" step names ({len(step_names)})"
            )
        if len(lane) != len(step_durations):
            raise ValueError(
                f"Number of steps in lane ({len(lane)}) does not match number of"
                f" step durations ({len(step_durations)})"
            )
        self.lane = lane
        self.steps = list(zip(step_names, step_durations))

    def compile_trigger(
        self, variables: VariableNamespace, time_step: int
    ) -> SequencerInstruction[np.bool_]:
        step_durations = evaluate_step_durations(self.steps, variables)
        step_bounds = get_step_bounds(step_durations)

        instructions = []
        for value, (start, stop) in zip(self.lane.values(), self.lane.bounds()):
            length = number_ticks(step_bounds[start], step_bounds[stop], time_step * ns)
            if isinstance(value, TakePicture):
                if length == 0:
                    raise ValueError(
                        f"No trigger can be generated for picture "
                        f"'{value.picture_name}' because its exposure is too short"
                        f"({(step_bounds[stop] - step_bounds[start])*1e9} ns) with "
                        f"respect to the time step ({time_step} ns)"
                    )
                instructions.append(Pattern([True]) * length)
            elif value is None:
                instructions.append(Pattern([False]) * length)
            else:
                assert_never(value)
        return join(*instructions)

    def compile_exposures(self, variables: VariableNamespace) -> list[float]:
        step_durations = evaluate_step_durations(self.steps, variables)

        exposures = []
        for value, (start, stop) in zip(self.lane.values(), self.lane.bounds()):
            if isinstance(value, TakePicture):
                exposure = sum(step_durations[start:stop])
                exposures.append(exposure)
        return exposures
