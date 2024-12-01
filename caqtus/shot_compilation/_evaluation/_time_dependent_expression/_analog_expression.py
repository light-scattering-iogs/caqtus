from typing import assert_type

import attrs
import numpy as np

import caqtus_parsing.nodes as nodes
from caqtus.shot_compilation.timed_instructions import TimedInstruction, Pattern
from caqtus.shot_compilation.timing import Time, number_ticks
from caqtus.types.parameter import Parameters
from caqtus.types.units import BaseUnit, dimensionless, Quantity
from ._is_time_dependent import is_time_dependent
from .._evaluate_scalar_expression import evaluate_expression


@attrs.define
class AnalogInstruction:
    magnitudes: TimedInstruction[np.float64]
    units: BaseUnit


def evaluate_analog_ast(
    ast: nodes.Expression, parameters: Parameters, t1: Time, t2: Time, timestep: Time
) -> AnalogInstruction:
    if not is_time_dependent(ast):
        value = evaluate_expression(ast, parameters)
        length = number_ticks(t1, t2, timestep)
        if isinstance(value, (bool, int, float)):
            return AnalogInstruction(
                magnitudes=Pattern([float(value)]) * length,
                units=dimensionless,
            )
        else:
            assert_type(value, Quantity[float])
            in_base_units = value.to_base_units()
            return AnalogInstruction(
                magnitudes=Pattern([in_base_units.magnitude]) * length,
                units=in_base_units.units,
            )
    else:
        raise NotImplementedError
