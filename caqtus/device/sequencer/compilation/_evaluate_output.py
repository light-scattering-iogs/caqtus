import functools
from collections.abc import Mapping
from typing import (
    Optional,
    Any,
)

import numpy as np

from caqtus.device.sequencer.compilation import evaluate_device_trigger
from caqtus.device.sequencer.instructions import SequencerInstruction, Pattern
from caqtus.shot_compilation import (
    ShotContext,
)
from caqtus.types.expression import Expression
from caqtus.types.parameter import magnitude_in_unit
from caqtus.types.units import Unit
from caqtus.types.variable_name import DottedVariableName
from ..configuration import (
    ChannelOutput,
    Advance,
    Delay,
    DeviceTrigger,
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


@evaluate_output.register
def _(
    output_: DeviceTrigger,
    required_time_step: int,
    required_unit: Optional[Unit],
    prepend: int,
    append: int,
    shot_context: ShotContext,
) -> SequencerInstruction[np.bool_]:
    device = output_.device_name
    try:
        device_config = shot_context.get_device_config(device)
    except KeyError:
        if output_.default is not None:
            return evaluate_output(
                output_.default,
                required_time_step,
                required_unit,
                prepend,
                append,
                shot_context,
            )
        else:
            raise ValueError(
                f"Could not find device <{device}> when evaluating output "
                f"<{output_}>"
            )
    if required_unit is not None:
        raise ValueError(
            f"Cannot evaluate trigger for device <{device}> with unit "
            f"{required_unit:~}"
        )
    trigger_values = evaluate_device_trigger(
        device, device_config, required_time_step, shot_context
    )
    return prepend * Pattern([False]) + trigger_values + append * Pattern([False])


def _evaluate_expression_in_unit(
    expression: Expression,
    required_unit: Optional[Unit],
    variables: Mapping[DottedVariableName, Any],
) -> np.floating:
    value = expression.evaluate(variables)
    magnitude = magnitude_in_unit(value, required_unit)
    return magnitude
