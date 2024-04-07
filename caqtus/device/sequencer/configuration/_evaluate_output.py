import functools
from collections.abc import Mapping
from typing import (
    Optional,
    Any,
)

import numpy as np

from caqtus.session.shot import DigitalTimeLane, AnalogTimeLane
from caqtus.shot_compilation import (
    ShotContext,
)
from caqtus.shot_compilation.lane_compilers.timing import number_ticks, ns
from caqtus.types.expression import Expression
from caqtus.types.parameter import magnitude_in_unit, add_unit
from caqtus.types.units import Unit
from caqtus.types.variable_name import DottedVariableName
from caqtus.utils import add_exc_note
from ._compile_digital_lane import compile_digital_lane
from ._generate_device_trigger import evaluate_device_trigger
from .channel_output import (
    ChannelOutput,
    Advance,
    Delay,
    Constant,
    LaneValues,
    CalibratedAnalogMapping,
    DeviceTrigger,
)
from .compile_analog_lane import compile_analog_lane
from ..instructions import SequencerInstruction, Pattern


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
    output_: Constant,
    required_time_step: int,
    required_unit: Optional[Unit],
    prepend: int,
    append: int,
    shot_context: ShotContext,
) -> SequencerInstruction:
    """Evaluate a constant output.

    Returns an instruction that has constant values for the entire shot duration.
    The constant value is obtained by evaluating the value stored in the constant
    output within the shot namespace.
    Note that `constant` refers to a value constant in shot time, not necessarily
    constant across shots.
    """

    length = (
        number_ticks(0, shot_context.get_shot_duration(), required_time_step * ns)
        + prepend
        + append
    )
    expression = output_.value
    value = expression.evaluate(shot_context.get_variables())
    magnitude = magnitude_in_unit(value, required_unit)
    return Pattern([magnitude]) * length


@evaluate_output.register
def _(
    output_: LaneValues,
    required_time_step: int,
    required_unit: Optional[Unit],
    prepend: int,
    append: int,
    shot_context: ShotContext,
) -> SequencerInstruction:
    """Evaluate the output of a channel as the values of a lane.

    This function will look in the shot time lanes to find the lane referenced by
    the output and evaluate the values of this lane.
    If the lane cannot be found, and the output has a default value, this default
    value will be used.
    If the lane cannot be found and there is no default value, a ValueError will be
    raised.
    """

    lane_name = output_.lane
    try:
        lane = shot_context.get_lane(lane_name)
    except KeyError:
        if output_.default is not None:
            constant = Constant(output_.default)
            return evaluate_output(
                constant,
                required_time_step,
                required_unit,
                prepend,
                append,
                shot_context,
            )
        else:
            raise ValueError(
                f"Could not find lane <{lane_name}> when evaluating output "
                f"<{output_}>"
            )
    if isinstance(lane, DigitalTimeLane):
        if required_unit is not None:
            raise ValueError(
                f"Cannot evaluate digital lane <{lane_name}> with unit "
                f"{required_unit:~}"
            )
        with add_exc_note(f"When evaluating digital lane <{lane_name}>"):
            lane_values = compile_digital_lane(lane, required_time_step, shot_context)
    elif isinstance(lane, AnalogTimeLane):
        with add_exc_note(f"When evaluating analog lane <{lane_name}>"):
            lane_values = compile_analog_lane(
                lane, required_unit, required_time_step, shot_context
            )
    else:
        raise TypeError(f"Cannot evaluate values of lane with type {type(lane)}")
    prepend_pattern = prepend * Pattern([lane_values[0]])
    append_pattern = append * Pattern([lane_values[-1]])
    return prepend_pattern + lane_values + append_pattern


@evaluate_output.register
def _(
    mapping: CalibratedAnalogMapping,
    required_time_step: int,
    required_unit: Optional[Unit],
    prepend: int,
    append: int,
    shot_context: ShotContext,
) -> SequencerInstruction[np.floating]:
    input_values = evaluate_output(
        mapping.input_,
        required_time_step,
        mapping.input_units,
        prepend,
        append,
        shot_context,
    )
    output_values = input_values.apply(mapping.interpolate)
    if required_unit != mapping.output_units:
        output_values = output_values.apply(
            functools.partial(
                _convert_units,
                input_unit=mapping.output_units,
                output_unit=required_unit,
            )
        )
    return output_values


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
        raise ValueError(
            f"Could not find device <{device}> to generate trigger "
            f"for output <{output_}>."
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


@evaluate_output.register
def evaluate_advanced_output(
    output_: Advance,
    required_time_step: int,
    required_unit: Optional[Unit],
    prepend: int,
    append: int,
    shot_context: ShotContext,
) -> SequencerInstruction:
    evaluated_advance = _evaluate_expression_in_unit(
        output_.advance, Unit("ns"), shot_context.get_variables()
    )
    number_ticks_to_advance = round(evaluated_advance / required_time_step)
    if number_ticks_to_advance < 0:
        raise ValueError(
            f"Cannot advance by a negative number of time steps "
            f"({number_ticks_to_advance})"
        )
    if number_ticks_to_advance > prepend:
        raise ValueError(
            f"Cannot advance by {number_ticks_to_advance} time steps when only "
            f"{prepend} are available"
        )
    return evaluate_output(
        output_.input_,
        required_time_step,
        required_unit,
        prepend - number_ticks_to_advance,
        append + number_ticks_to_advance,
        shot_context,
    )


@evaluate_output.register
def evaluate_delayed_output(
    output_: Delay,
    required_time_step: int,
    required_unit: Optional[Unit],
    prepend: int,
    append: int,
    shot_context: ShotContext,
) -> SequencerInstruction:
    evaluated_delay = _evaluate_expression_in_unit(
        output_.delay, Unit("ns"), shot_context.get_variables()
    )
    number_ticks_to_delay = round(evaluated_delay / required_time_step)
    if number_ticks_to_delay < 0:
        raise ValueError(
            f"Cannot delay by a negative number of time steps "
            f"({number_ticks_to_delay})"
        )
    return evaluate_output(
        output_.input_,
        required_time_step,
        required_unit,
        prepend + number_ticks_to_delay,
        append - number_ticks_to_delay,
        shot_context,
    )


def _evaluate_expression_in_unit(
    expression: Expression,
    required_unit: Optional[Unit],
    variables: Mapping[DottedVariableName, Any],
) -> np.floating:
    value = expression.evaluate(variables)
    magnitude = magnitude_in_unit(value, required_unit)
    return magnitude


def _convert_units(
    array: np.ndarray, input_unit: Optional[str], output_unit: Optional[str]
) -> np.ndarray:
    if input_unit == output_unit:
        return array
    return magnitude_in_unit(add_unit(array, input_unit), output_unit)  # type: ignore
