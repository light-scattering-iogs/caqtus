from collections.abc import Mapping
from typing import TypeGuard, Any, TypeAlias

from caqtus.utils import serialization
from ._analog_value import Quantity, ScalarAnalogValue, is_scalar_analog_value
from ..variable_name import DottedVariableName

Parameter: TypeAlias = ScalarAnalogValue | int | bool

type Parameters = Mapping[DottedVariableName, Parameter]

converter = serialization.copy_converter()
"""A converter that can serialize and deserialize parameters."""


@converter.register_unstructure_hook
def unstructure_quantity(value: Quantity):
    return float(value.magnitude), f"{value.units:~}"


@converter.register_structure_hook
def structure_quantity(value: Any, _) -> Quantity:
    try:
        return Quantity(*value)  # pyright: ignore[reportReturnType]
    except TypeError:
        raise ValueError(f"Cannot structure {value!r} as a Quantity.") from None


serialization.register_unstructure_hook(Quantity, unstructure_quantity)

serialization.register_structure_hook(Quantity, structure_quantity)


def _structure_quantity(value: Any, _) -> Quantity:
    try:
        return Quantity(*value)  # pyright: ignore[reportReturnType]
    except TypeError:
        raise ValueError(f"Cannot structure {value!r} as a Quantity.") from None


def is_parameter(parameter: Any) -> TypeGuard[Parameter]:
    """Returns True if the value is a valid parameter type, False otherwise."""

    return is_scalar_analog_value(parameter) or isinstance(parameter, (int, bool))
