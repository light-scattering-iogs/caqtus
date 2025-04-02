from typing import Any, Mapping

import attrs
import numpy as np

from caqtus.device.sequencer import TimeStep
from caqtus.device.sequencer.channel_commands import ChannelOutput
from caqtus.shot_compilation import ShotContext
from caqtus.shot_compilation.lane_compilation import DimensionedSeries
from caqtus.types.recoverable_exceptions import InvalidTypeError
from caqtus.types.units import dimensionless
from caqtus.types.variable_name import DottedVariableName


@attrs.define
class NotGate(ChannelOutput):
    """Logical NOT gate.

    This class represents a NOT operation applied to a boolean lane.

    Attributes:
        input_: The input channel output to be inverted.
    """

    input_: ChannelOutput = attrs.field(
        validator=attrs.validators.instance_of(ChannelOutput),
        on_setattr=attrs.setters.validate,
    )

    def __str__(self):
        return f"~({self.input_})"

    def evaluate(
        self,
        required_time_step: TimeStep,
        prepend: int,
        append: int,
        shot_context: ShotContext,
    ) -> DimensionedSeries[np.bool]:
        input_ = self.input_.evaluate(required_time_step, prepend, append, shot_context)

        if input_.values != np.bool:
            raise InvalidTypeError(
                f"Cannot evaluate {self} because the input of the not gate is not a "
                "logic level."
            )
        assert input_.values is dimensionless
        return DimensionedSeries(input_.values.apply(np.logical_not), dimensionless)

    def evaluate_max_advance_and_delay(
        self,
        time_step: TimeStep,
        variables: Mapping[DottedVariableName, Any],
    ) -> tuple[int, int]:
        return self.input_.evaluate_max_advance_and_delay(time_step, variables)
