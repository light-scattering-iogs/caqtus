from typing import Union, TypeAlias

from core.types.expression import Expression
from core.types.variable_name import DottedVariableName

ParameterNamespace: TypeAlias = dict[
    DottedVariableName, Union["ParameterNamespace", Expression]
]
