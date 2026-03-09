from collections.abc import Sequence
from typing import assert_never

import numpy as np

from caqtus.shot_compilation.timed_instructions import (
    TimedInstruction,
    Pattern,
    concatenate,
)
from caqtus.types.expression import Expression
from caqtus.types.parameter import Parameters
from caqtus.types.timelane import DigitalTimeLane
from .._evaluation import evaluate_time_dependent_digital_expression
from ..timing import Time, number_ticks


def compile_digital_lane(
    lane: DigitalTimeLane,
    step_start_times: Sequence[Time],
    time_step: Time,
    parameters: Parameters,
) -> TimedInstruction[np.bool]:
    """Compile a digital lane into a sequence of instructions.

    Args:
        lane: The digital lane to compile.
        step_start_times: The start times of each step.
            The length of this sequence must be equal to the number of steps in the
            lane plus one, with the last element being the total duration.
        time_step: The time step for discretizing the time, in seconds.
        parameters: The parameters to use when evaluating expressions in the lane.
    """

    if len(lane) != len(step_start_times) - 1:
        raise ValueError(
            f"Number of steps in lane ({len(lane)}) does not match number of step "
            f"start times ({len(step_start_times) - 1})"
        )

    instructions = []
    for cell_value, (start, stop) in zip(
        lane.block_values(), lane.block_bounds(), strict=True
    ):
        if isinstance(cell_value, bool):
            length = number_ticks(
                step_start_times[start], step_start_times[stop], time_step
            )
            instructions.append(Pattern([cell_value]) * length)
        elif isinstance(cell_value, Expression):
            instr = evaluate_time_dependent_digital_expression(
                cell_value,
                parameters,
                step_start_times[start],
                step_start_times[stop],
                time_step,
            )
            instructions.append(instr)
        else:
            assert_never(cell_value)
    return concatenate(*instructions)
