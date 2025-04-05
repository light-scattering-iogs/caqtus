from __future__ import annotations

import abc
from builtins import float
from typing import Generic, Self, assert_never

import attrs
from typing_extensions import TypeVar

from ...types.parameter import Parameter, ParameterType
from ...types.parameter._schema import Boolean, Float, Integer, QuantityType
from ...types.units import Quantity, Unit, dimensionless


class CompiledExpression(abc.ABC):
    @abc.abstractmethod
    def __neg__(self) -> CompiledExpression:
        raise NotImplementedError

    @abc.abstractmethod
    def __pos__(self) -> CompiledExpression:
        raise NotImplementedError


type _CompiledExpression = Constant | ConstantParameter | VariableParameter | Negate

T = TypeVar("T", bound=Parameter, default=Parameter, covariant=True)


@attrs.frozen
class Constant(CompiledExpression, Generic[T]):
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

    def __neg__(self) -> Constant[int | float | Quantity[float, Unit]]:
        match self.value:
            case bool():
                raise TypeError(f"Cannot negate boolean literal {self}.")
            case float(x) | int(x):
                return Constant(-x)
            case Quantity() as quantity:
                return Constant(-1.0 * quantity)
            case _:
                assert_never(self.value)

    def __pos__(self) -> Constant[int | float | Quantity[float, Unit]]:
        match self.value:
            case bool():
                raise TypeError(f"Cannot apply unary plus to boolean literal {self}.")
            case float(x) | int(x):
                return Constant(+x)
            case Quantity() as quantity:
                return Constant(+1.0 * quantity)
            case _:
                assert_never(self.value)

    def __add__(self, other: _CompiledExpression) -> _CompiledExpression:
        if isinstance(other, Constant):
            return _add_constants(self, other)
        else:
            raise NotImplementedError


def _add_constants(left: Constant, right: Constant) -> Constant:
    lhs = left.value
    rhs = right.value
    if isinstance(lhs, bool):
        raise TypeError(f"Cannot add boolean constant {left} to {right}.")
    if isinstance(rhs, bool):
        raise TypeError(f"Cannot add {left} to boolean constant {right}.")
    match lhs:
        case int(x):
            match rhs:
                case int(y):
                    return Constant[int](x + y)
                case float(y):
                    return Constant[float](x + y)
                case Quantity() as y:
                    if not y.units.is_compatible_with(dimensionless):
                        raise TypeError(
                            f"Cannot add dimensionless {left} to {right} with units "
                            f"{y.units:~}"
                        )
                    return Constant[float](x + y.to_unit(dimensionless).magnitude)
                case _:
                    assert_never(rhs)
        case float(x):
            match rhs:
                case int(y) | float(y):
                    return Constant[float](x + y)
                case Quantity() as y:
                    if not y.units.is_compatible_with(dimensionless):
                        raise TypeError(
                            f"Cannot add dimensionless {left} to {right} with units "
                            f"{y.units:~}"
                        )
                    return Constant[float](x + y.to_unit(dimensionless).magnitude)
                case _:
                    assert_never(rhs)
        case Quantity() as x:
            match rhs:
                case int(y) | float(y):
                    if not x.units.is_compatible_with(dimensionless):
                        raise TypeError(
                            f"Cannot add {left} with units {x.units:~} to "
                            f"dimensionless {right}"
                        )
                    x_base = x.to_unit(dimensionless)
                    return Constant(
                        Quantity(x_base.magnitude + y, dimensionless).to_unit(x.units)
                    )
                case Quantity() as y:
                    if not x.units.is_compatible_with(y.units):
                        raise TypeError(
                            f"Cannot add {left} with units {x.units:~} to "
                            f"{right} with units {y.units:~}"
                        )
                    x_base = x.to_base_units()
                    y_base = y.to_base_units()
                    return Constant(
                        Quantity(
                            x_base.magnitude + y_base.magnitude, x_base.units
                        ).to_unit(x.units)
                    )
                case _:
                    assert_never(rhs)
        case _:
            assert_never(lhs)


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

    def __pos__(self) -> _CompiledExpression:
        match self.value:
            case bool():
                raise TypeError(f"Cannot apply unary plus to boolean parameter {self}.")
            case _:
                return self


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

    def __pos__(self) -> Self:
        if isinstance(self.type_, Boolean):
            raise TypeError(f"Cannot apply unary plus to boolean parameter {self}.")
        return self


@attrs.frozen
class Negate(CompiledExpression):
    operand: (
        ConstantParameter[int | float | Quantity[float, Unit]]
        | VariableParameter[Integer | Float | QuantityType]
    )

    def __neg__(self) -> _CompiledExpression:
        return self.operand

    def __pos__(self) -> Self:
        return self
