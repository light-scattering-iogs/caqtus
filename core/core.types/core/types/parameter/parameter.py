from typing import TypeGuard, Any

from util import serialization
from .analog_value import AnalogValue, is_analog_value, Quantity

Parameter = AnalogValue | int | bool


def unstructure_quantity(value: Quantity):
    return float(value.magnitude), str(value.units)


def structure_quantity(value: Any, _) -> Quantity:
    try:
        return Quantity(*value)
    except TypeError:
        raise ValueError(f"Cannot structure {value!r} as a Quantity.")


serialization.register_unstructure_hook(Quantity, unstructure_quantity)

serialization.register_structure_hook(Quantity, structure_quantity)


def is_parameter(parameter: Any) -> TypeGuard[Parameter]:
    """Returns True if the value is a valid parameter type, False otherwise."""

    return is_analog_value(parameter) or isinstance(parameter, (int, bool))
