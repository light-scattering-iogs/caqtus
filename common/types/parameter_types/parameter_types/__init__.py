from typing import Any, TypeGuard

from units import AnalogValue, is_analog_value

ParameterType = AnalogValue | int | bool


def is_valid_parameter_type(parameter: Any) -> TypeGuard[ParameterType]:
    """Returns True if the value is a valid parameter type, False otherwise."""

    return is_analog_value(parameter) or isinstance(parameter, (int, bool))
