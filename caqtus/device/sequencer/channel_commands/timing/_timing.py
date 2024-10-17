from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import attrs

from caqtus.shot_compilation import ShotContext
from caqtus.types.expression import Expression
from caqtus.types.recoverable_exceptions import InvalidValueError
from caqtus.types.units import (
    is_scalar_quantity,
    DimensionalityError,
    InvalidDimensionalityError,
    NANOSECOND,
)
from caqtus.types.variable_name import DottedVariableName
from ..channel_output import ChannelOutput
from ...timing import TimeStep


@attrs.define
class Advance(ChannelOutput):
    input_: ChannelOutput = attrs.field(
        validator=attrs.validators.instance_of(ChannelOutput),
        on_setattr=attrs.setters.validate,
    )
    advance: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )

    def __str__(self):
        return f"{self.input_} << {self.advance}"

    def evaluate(
        self,
        required_time_step: TimeStep,
        prepend: int,
        append: int,
        shot_context: ShotContext,
    ):
        evaluated_advance = _evaluate_in_nanoseconds(
            self.advance, shot_context.get_parameters()
        )
        number_ticks_to_advance = round(evaluated_advance / float(required_time_step))
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
        return self.input_.evaluate(
            required_time_step,
            prepend - number_ticks_to_advance,
            append + number_ticks_to_advance,
            shot_context,
        )

    def evaluate_max_advance_and_delay(
        self,
        time_step: TimeStep,
        variables: Mapping[DottedVariableName, Any],
    ) -> tuple[int, int]:
        advance = _evaluate_in_nanoseconds(self.advance, variables)
        if advance < 0:
            raise InvalidValueError("Advance must be a positive number.")
        advance_ticks = round(advance / float(time_step))
        input_advance, input_delay = self.input_.evaluate_max_advance_and_delay(
            time_step, variables
        )
        return advance_ticks + input_advance, input_delay


@attrs.define
class Delay(ChannelOutput):
    input_: ChannelOutput = attrs.field(
        validator=attrs.validators.instance_of(ChannelOutput),
        on_setattr=attrs.setters.validate,
    )
    delay: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )

    def __str__(self):
        return f"{self.delay} >> {self.input_}"

    def evaluate(
        self,
        required_time_step: TimeStep,
        prepend: int,
        append: int,
        shot_context: ShotContext,
    ):
        evaluated_delay = _evaluate_in_nanoseconds(
            self.delay, shot_context.get_parameters()
        )
        number_ticks_to_delay = round(evaluated_delay / float(required_time_step))
        if number_ticks_to_delay < 0:
            raise ValueError(
                f"Cannot delay by a negative number of time steps "
                f"({number_ticks_to_delay})"
            )
        if number_ticks_to_delay > append:
            raise ValueError(
                f"Cannot delay by {number_ticks_to_delay} time steps when only "
                f"{append} are available"
            )
        return self.input_.evaluate(
            required_time_step,
            prepend + number_ticks_to_delay,
            append - number_ticks_to_delay,
            shot_context,
        )

    def evaluate_max_advance_and_delay(
        self,
        time_step: TimeStep,
        variables: Mapping[DottedVariableName, Any],
    ) -> tuple[int, int]:
        delay = _evaluate_in_nanoseconds(self.delay, variables)
        if delay < 0:
            raise ValueError("Delay must be a positive number.")
        delay_ticks = round(delay / float(time_step))
        input_advance, input_delay = self.input_.evaluate_max_advance_and_delay(
            time_step, variables
        )
        return input_advance, delay_ticks + input_delay


def _evaluate_in_nanoseconds(
    expression: Expression, variables: Mapping[DottedVariableName, Any]
) -> float:
    evaluated = expression.evaluate(variables)
    if not is_scalar_quantity(evaluated):
        raise InvalidValueError("Advance must be a scalar quantity.")
    try:
        evaluated_advance = evaluated.to_unit(NANOSECOND).magnitude
    except DimensionalityError as e:
        raise InvalidDimensionalityError(
            f"Advance must be expressed in seconds, not {evaluated.units}"
        ) from e
    return evaluated_advance
