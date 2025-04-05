from __future__ import annotations

import abc
from typing import Generic, assert_never

import attrs
from typing_extensions import TypeVar

from ...types.parameter import Parameter, ParameterType
from ...types.parameter._schema import Boolean, Float, Integer, QuantityType
from ...types.units import Quantity, Unit


class CompiledExpression(abc.ABC):
    @abc.abstractmethod
    def __neg__(self) -> CompiledExpression:
        raise NotImplementedError


type _CompiledExpression = Literal | ConstantParameter | VariableParameter | Negate

T = TypeVar("T", bound=Parameter, default=Parameter, covariant=True)


@attrs.frozen
class Literal(CompiledExpression, Generic[T]):
    value: T

    def __str__(self):
        match self.value:
            case bool():
                return str(self.value).lower()
            case float(x) | int(x):
                return str(x)
            case Quantity() as quantity:
                return str(quantity)
            case _:
                assert_never(self.value)

    def __neg__(self) -> Literal[int | float | Quantity[float, Unit]]:
        match self.value:
            case bool():
                raise TypeError(f"Cannot negate boolean literal {self}.")
            case float(x) | int(x):
                return Literal(-x)
            case Quantity() as quantity:
                return Literal(-1.0 * quantity)
            case _:
                assert_never(self.value)


@attrs.frozen
class ConstantParameter(CompiledExpression, Generic[T]):
    value: T
    name: str

    def __str__(self):
        return f"{self.name} = {self.value}"

    def __neg__(self) -> _CompiledExpression:
        match self.value:
            case bool():
                raise TypeError(f"Cannot negate boolean parameter {self}.")
            case _:
                return Negate(self)


PT = TypeVar("PT", bound=ParameterType, default=ParameterType, covariant=True)


@attrs.frozen
class VariableParameter(CompiledExpression, Generic[PT]):
    type_: PT
    name: str

    def __str__(self):
        return f"{self.name}"

    def __neg__(
        self,
    ) -> Negate:
        if isinstance(self.type_, Boolean):
            raise TypeError(f"Cannot negate boolean parameter {self}.")
        return Negate(VariableParameter(self.type_, self.name))


@attrs.frozen
class Negate(CompiledExpression):
    operand: (
        ConstantParameter[int | float | Quantity[float, Unit]]
        | VariableParameter[Integer | Float | QuantityType]
    )

    def __neg__(self) -> _CompiledExpression:
        return self.operand
