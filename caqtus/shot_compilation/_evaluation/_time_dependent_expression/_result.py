import attrs
import numpy as np

from caqtus.shot_compilation.timed_instructions import TimedInstruction
from caqtus.types.units import BaseUnit
from caqtus.types.units.base import is_in_base_units


@attrs.frozen
class IntResult:
    values: TimedInstruction[np.int64]
    initial_value: int = attrs.field()
    final_value: int = attrs.field()


@attrs.frozen
class FloatResult:
    values: TimedInstruction[np.float64]
    initial_value: float = attrs.field()
    final_value: float = attrs.field()


@attrs.frozen
class BoolResult:
    values: TimedInstruction[np.bool]
    initial_value: bool = attrs.field()
    final_value: bool = attrs.field()


@attrs.frozen
class QuantityResult:
    values: TimedInstruction[np.float64]
    initial_value: float = attrs.field()
    final_value: float = attrs.field()
    unit: BaseUnit = attrs.field()

    @unit.validator  # type: ignore[reportAttributeAccessIssue]
    def _validate_unit(self, attribute, value):
        if not is_in_base_units(value):
            raise AssertionError(f"Unit {value} is not in base units.")


type EvaluationResult = IntResult | FloatResult | BoolResult | QuantityResult
