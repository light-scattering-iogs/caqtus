from typing import Any, TypeGuard

from units import AnalogValue, is_analog_value

Parameter = AnalogValue | int | bool


def is_parameter(parameter: Any) -> TypeGuard[Parameter]:
    """Returns True if the value is a valid parameter type, False otherwise."""

    return is_analog_value(parameter) or isinstance(parameter, (int, bool))
