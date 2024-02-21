from typing import Union, TypeAlias, Any, TypeGuard

from core.types.expression import Expression
from core.types.variable_name import DottedVariableName
from util import serialization

ParameterNamespace: TypeAlias = dict[
    DottedVariableName, Union["ParameterNamespace", Expression]
]


def structure_hook(value, _) -> Union[Expression, ParameterNamespace]:
    if isinstance(value, str):
        return Expression(value)
    elif isinstance(value, dict):
        return serialization.structure(value, ParameterNamespace)
    else:
        raise ValueError(f"Invalid value {value}")


serialization.register_structure_hook(
    Union["ParameterNamespace", Expression], structure_hook
)


def is_parameter_namespace(value: Any) -> TypeGuard[ParameterNamespace]:
    if not isinstance(value, dict):
        return False

    for key, value in value.items():
        if not isinstance(key, DottedVariableName):
            return False
        if not (isinstance(value, Expression) or is_parameter_namespace(value)):
            return False
    return True
