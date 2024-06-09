import functools
from collections.abc import Mapping
from typing import (
    Optional,
    Any,
)

import numpy as np

from caqtus.device.sequencer.instructions import SequencerInstruction
from caqtus.shot_compilation import (
    ShotContext,
)
from caqtus.types.expression import Expression
from caqtus.types.parameter import magnitude_in_unit
from caqtus.types.units import Unit
from caqtus.types.variable_name import DottedVariableName
from ..configuration import (
    ChannelOutput,
)


@functools.singledispatch
def evaluate_output(
    output_: ChannelOutput,
    required_time_step: int,
    required_unit: Optional[Unit],
    prepend: int,
    append: int,
    shot_context: "ShotContext",
) -> SequencerInstruction:
    """Evaluate the output of a channel with the required parameters.

    Args:
        output_: The output to evaluate.
        required_time_step: The time step of the sequencer that will use the
        output, in ns.
        required_unit: The unit in which the output should be expressed when
        evaluated.
        prepend: The number of time steps to add at the beginning of the output.
        append: The number of time steps to add at the end of the output.
        shot_context: The context of the shot in which the output is evaluated.
    """

    raise NotImplementedError(f"Cannot evaluate output <{output_}>")


def _evaluate_expression_in_unit(
    expression: Expression,
    required_unit: Optional[Unit],
    variables: Mapping[DottedVariableName, Any],
) -> np.floating:
    value = expression.evaluate(variables)
    magnitude = magnitude_in_unit(value, required_unit)
    return magnitude
