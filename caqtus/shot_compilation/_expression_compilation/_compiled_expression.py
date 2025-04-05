import abc

import attrs

from ...types.parameter import Parameter, ParameterType


class CompiledExpression(abc.ABC):
    pass


type _CompiledExpression = Literal | ConstantParameter | VariableParameter


@attrs.frozen
class Literal(CompiledExpression):
    value: Parameter


@attrs.frozen
class ConstantParameter(CompiledExpression):
    value: Parameter
    name: str


@attrs.frozen
class VariableParameter(CompiledExpression):
    type_: ParameterType
    name: str

