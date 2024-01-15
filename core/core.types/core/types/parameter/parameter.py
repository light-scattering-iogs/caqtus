from typing import TypeGuard, Any

from util import serialization
from .analog_value import AnalogValue, is_analog_value, Quantity

Parameter = AnalogValue | int | bool


def unstructure_quantity(value: Quantity):
    return float(value.magnitude), str(value.units)


def structure_quantity(value: Any, _) -> Quantity:
    if isinstance(value, tuple) and len(value) == 2:
        return Quantity(*value)
    else:
        raise ValueError(f"Expected tuple of length 2, got {value}")


serialization.register_unstructure_hook(Quantity, unstructure_quantity)

serialization.register_structure_hook(Quantity, structure_quantity)


def is_parameter(parameter: Any) -> TypeGuard[Parameter]:
    """Returns True if the value is a valid parameter type, False otherwise."""

    return is_analog_value(parameter) or isinstance(parameter, (int, bool))
