import functools
from typing import Any, Mapping

import attrs
import numpy as np

from caqtus.device.sequencer import TimeStep
from caqtus.device.sequencer.channel_commands import ChannelOutput
from caqtus.shot_compilation import ShotContext
from caqtus.shot_compilation.lane_compilation import DimensionedSeries
from caqtus.shot_compilation.timed_instructions import (
    Concatenated,
    Pattern,
    Repeated,
    TimedInstruction,
    concatenate,
    merge_instructions,
)
from caqtus.types.recoverable_exceptions import InvalidTypeError
from caqtus.types.units import dimensionless
from caqtus.types.variable_name import DottedVariableName


@attrs.define
class AndGate(ChannelOutput):
    """Logical AND gate.

    This class represents a AND operation applied to two boolean lanes.

    Attributes:
        input_1: The first input channel output to be ANDed.
        input_2: The second input channel output to be ANDed.
    """

    input_1: ChannelOutput = attrs.field(
        validator=attrs.validators.instance_of(ChannelOutput),
        on_setattr=attrs.setters.validate,
    )
    input_2: ChannelOutput = attrs.field(
        validator=attrs.validators.instance_of(ChannelOutput),
        on_setattr=attrs.setters.validate,
    )

    def __str__(self):
        return f"({self.input_1} & {self.input_2})"

    def evaluate(
        self,
        required_time_step: TimeStep,
        prepend: int,
        append: int,
        shot_context: ShotContext,
    ) -> DimensionedSeries[np.bool]:
        input_1 = self.input_1.evaluate(
            required_time_step, prepend, append, shot_context
        )
        if input_1.values.dtype != np.bool:
            raise InvalidTypeError(
                f"Cannot evaluate {self} because the first input of the and gate is "
                f"not a logic level."
            )
        assert input_1.units is dimensionless
        input_2 = self.input_2.evaluate(
            required_time_step, prepend, append, shot_context
        )
        if input_2.values.dtype != np.bool:
            raise InvalidTypeError(
                f"Cannot evaluate {self} because the second input of the and gate is "
                f"not a logic level."
            )
        assert input_2.units is dimensionless
        merged = merge_instructions(
            lhs=input_1.values,
            rhs=input_2.values,
        )
        result = binary_operator(merged, np.logical_and)
        return DimensionedSeries(result, dimensionless)

    def evaluate_max_advance_and_delay(
        self,
        time_step: TimeStep,
        variables: Mapping[DottedVariableName, Any],
    ) -> tuple[int, int]:
        advance_1, delay_1 = self.input_1.evaluate_max_advance_and_delay(
            time_step, variables
        )
        advance_2, delay_2 = self.input_2.evaluate_max_advance_and_delay(
            time_step, variables
        )
        advance = max(advance_1, advance_2)
        delay = max(delay_1, delay_2)
        return advance, delay


@attrs.define
class OrGate(ChannelOutput):
    """Logical OR gate.

    This class represents a OR operation applied to two boolean lanes.

    Attributes:
        input_1: The first input channel output to be ORed.
        input_2: The second input channel output to be ORed.
    """

    input_1: ChannelOutput = attrs.field(
        validator=attrs.validators.instance_of(ChannelOutput),
        on_setattr=attrs.setters.validate,
    )
    input_2: ChannelOutput = attrs.field(
        validator=attrs.validators.instance_of(ChannelOutput),
        on_setattr=attrs.setters.validate,
    )

    def __str__(self):
        return f"({self.input_1} | {self.input_2})"

    def evaluate(
        self,
        required_time_step: TimeStep,
        prepend: int,
        append: int,
        shot_context: ShotContext,
    ) -> DimensionedSeries[np.bool]:
        input_1 = self.input_1.evaluate(
            required_time_step, prepend, append, shot_context
        )
        if input_1.values.dtype != np.bool:
            raise InvalidTypeError(
                f"Cannot evaluate {self} because the first input of the or gate is "
                f"not a logic level."
            )
        assert input_1.units is dimensionless
        input_2 = self.input_2.evaluate(
            required_time_step, prepend, append, shot_context
        )
        if input_2.values.dtype != np.bool:
            raise InvalidTypeError(
                f"Cannot evaluate {self} because the second input of the or gate is "
                f"not a logic level."
            )
        assert input_2.units is dimensionless
        merged = merge_instructions(
            lhs=input_1.values,
            rhs=input_2.values,
        )
        result = binary_operator(merged, np.logical_or)
        return DimensionedSeries(result, dimensionless)

    def evaluate_max_advance_and_delay(
        self,
        time_step: TimeStep,
        variables: Mapping[DottedVariableName, Any],
    ) -> tuple[int, int]:
        advance_1, delay_1 = self.input_1.evaluate_max_advance_and_delay(
            time_step, variables
        )
        advance_2, delay_2 = self.input_2.evaluate_max_advance_and_delay(
            time_step, variables
        )
        advance = max(advance_1, advance_2)
        delay = max(delay_1, delay_2)
        return advance, delay


@attrs.define
class XorGate(ChannelOutput):
    """Logical XOR gate.

    This class represents a XOR operation applied to two boolean lanes.

    Attributes:
        input_1: The first input channel output to be XORed.
        input_2: The second input channel output to be XORed.
    """

    input_1: ChannelOutput = attrs.field(
        validator=attrs.validators.instance_of(ChannelOutput),
        on_setattr=attrs.setters.validate,
    )
    input_2: ChannelOutput = attrs.field(
        validator=attrs.validators.instance_of(ChannelOutput),
        on_setattr=attrs.setters.validate,
    )

    def __str__(self):
        return f"({self.input_1} ^ {self.input_2})"

    def evaluate(
        self,
        required_time_step: TimeStep,
        prepend: int,
        append: int,
        shot_context: ShotContext,
    ) -> DimensionedSeries[np.bool]:
        input_1 = self.input_1.evaluate(
            required_time_step, prepend, append, shot_context
        )
        if input_1.values.dtype != np.bool:
            raise InvalidTypeError(
                f"Cannot evaluate {self} because the first input of the xor gate is "
                f"not a logic level."
            )
        assert input_1.units is dimensionless
        input_2 = self.input_2.evaluate(
            required_time_step, prepend, append, shot_context
        )
        if input_2.values.dtype != np.bool:
            raise InvalidTypeError(
                f"Cannot evaluate {self} because the second input of the xor gate is "
                f"not a logic level."
            )
        assert input_2.units is dimensionless
        merged = merge_instructions(
            lhs=input_1.values,
            rhs=input_2.values,
        )
        result = binary_operator(merged, np.logical_xor)
        return DimensionedSeries(result, dimensionless)

    def evaluate_max_advance_and_delay(
        self,
        time_step: TimeStep,
        variables: Mapping[DottedVariableName, Any],
    ) -> tuple[int, int]:
        advance_1, delay_1 = self.input_1.evaluate_max_advance_and_delay(
            time_step, variables
        )
        advance_2, delay_2 = self.input_2.evaluate_max_advance_and_delay(
            time_step, variables
        )
        advance = max(advance_1, advance_2)
        delay = max(delay_1, delay_2)
        return advance, delay


@functools.singledispatch
def binary_operator(instr: TimedInstruction, op) -> TimedInstruction:
    raise NotImplementedError(
        f"Cannot apply binary operator to instruction with type {type(instr)}"
    )


@binary_operator.register
def _(instr: Pattern, op) -> TimedInstruction:
    lhs = instr["lhs"]
    rhs = instr["rhs"]
    return Pattern.create_without_copy(op(lhs, rhs))


@binary_operator.register
def _(instr: Concatenated, op) -> TimedInstruction:
    result = []
    for instruction in instr.instructions:
        result.append(binary_operator(instruction, op))
    return concatenate(*result)


@binary_operator.register
def _(instr: Repeated, op) -> TimedInstruction:
    return instr.repetitions * binary_operator(instr.instruction, op)
