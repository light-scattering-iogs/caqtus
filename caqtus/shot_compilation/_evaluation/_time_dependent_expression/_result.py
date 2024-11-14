import attrs
import numpy as np

from caqtus.shot_compilation.timed_instructions import TimedInstruction
from caqtus.types.units import Unit, BaseUnit
from caqtus.types.units.base import is_in_base_units


@attrs.frozen
class EvaluationResult[T: (np.number, np.bool_)]:
    """Represents a series of value to output on a channel with their units.

    Parameters:
        values: The sequence of values to output.
        units: The units in which the values are expressed.
            They must be in base SI units.
    """

    values: TimedInstruction[T]
    units: BaseUnit = attrs.field()
    initial_value: T = attrs.field()
    final_value: T = attrs.field()

    @units.validator  # type: ignore[reportAttributeAccessIssue]
    def _validate_units(self, _, units):
        if not isinstance(units, Unit):
            raise TypeError(f"Expected a unit, got {type(units)}")
        if not is_in_base_units(units):
            raise ValueError(
                f"Unit {units} is not expressed in the base units of the registry."
            )
