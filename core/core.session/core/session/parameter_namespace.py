from typing import Union, TypeAlias, Any, TypeGuard

from core.types.expression import Expression
from core.types.variable_name import DottedVariableName

ParameterNamespace: TypeAlias = dict[
    DottedVariableName, Union["ParameterNamespace", Expression]
]


def is_parameter_namespace(value: Any) -> TypeGuard[ParameterNamespace]:
    if not isinstance(value, dict):
        return False

    for key, value in value.items():
        if not isinstance(key, DottedVariableName):
            return False
        if not (isinstance(value, Expression) or is_parameter_namespace(value)):
            return False
    return True
