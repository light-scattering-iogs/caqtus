import abc
from collections.abc import Callable

import attrs

from ...types.parameter import Parameters
from ...types.units import Quantity, Unit, dimensionless
from ._expression_type import (
    Boolean,
    ExpressionType,
    Float,
    Integer,
)
from ._expression_type import (
    Quantity as QuantityExprType,
)


class CompiledExpression(abc.ABC):
    @abc.abstractmethod
    def output_type(self) -> ExpressionType:
        """Return the type of the output of the expression."""

        raise NotImplementedError()

    @abc.abstractmethod
    def as_integer(self) -> Callable[[Parameters], int]:
        raise NotImplementedError()

    @abc.abstractmethod
    def as_float(self) -> Callable[[Parameters], float]:
        raise NotImplementedError()

    @abc.abstractmethod
    def as_quantity(self, unit: Unit) -> Callable[[Parameters], float]:
        raise NotImplementedError()

    @abc.abstractmethod
    def as_boolean(self) -> Callable[[Parameters], bool]:
        raise NotImplementedError()


type _CompiledExpression = (
    IntegerLiteral | FloatLiteral | BooleanLiteral | QuantityLiteral
)


@attrs.frozen
class IntegerLiteral(CompiledExpression):
    value: int

    def output_type(self) -> ExpressionType:
        return Integer()

    def as_integer(self) -> Callable[[Parameters], int]:
        return lambda _: self.value

    def as_float(self) -> Callable[[Parameters], float]:
        value = float(self.value)
        return lambda _: value

    def as_quantity(self, unit: Unit) -> Callable[[Parameters], float]:
        if unit.is_compatible_with(dimensionless):
            result = float(Quantity(self.value, dimensionless).to_unit(unit).magnitude)
            return lambda _: result
        else:
            raise ValueError(f"Cannot convert {self.value} to {unit}.")

    def as_boolean(self) -> Callable[[Parameters], bool]:
        raise ValueError(f"Cannot convert {self.value} to a boolean.")


@attrs.frozen
class FloatLiteral(CompiledExpression):
    value: float

    def output_type(self) -> ExpressionType:
        return Float()

    def as_integer(self) -> Callable[[Parameters], int]:
        raise ValueError(f"Cannot convert {self.value} to a integer.")

    def as_float(self) -> Callable[[Parameters], float]:
        return lambda _: self.value

    def as_quantity(self, unit: Unit) -> Callable[[Parameters], float]:
        if unit.is_compatible_with(dimensionless):
            result = float(Quantity(self.value, dimensionless).to_unit(unit).magnitude)
            return lambda _: result
        else:
            raise ValueError(f"Cannot convert {self.value} to {unit}.")

    def as_boolean(self) -> Callable[[Parameters], bool]:
        raise ValueError(f"Cannot convert {self.value} to a boolean.")


@attrs.frozen
class BooleanLiteral(CompiledExpression):
    value: bool

    def output_type(self) -> ExpressionType:
        return Boolean()

    def as_integer(self) -> Callable[[Parameters], int]:
        raise ValueError(f"Cannot convert {self.value} to a integer.")

    def as_float(self) -> Callable[[Parameters], float]:
        raise ValueError(f"Cannot convert {self.value} to a float.")

    def as_quantity(self, unit: Unit) -> Callable[[Parameters], float]:
        raise ValueError(f"Cannot convert {self.value} to a quantity.")

    def as_boolean(self) -> Callable[[Parameters], bool]:
        return lambda _: self.value


@attrs.frozen
class QuantityLiteral(CompiledExpression):
    value: float
    unit: Unit

    def __str__(self):
        return f"{self.value} {self.unit}"

    def output_type(self) -> ExpressionType:
        return QuantityExprType(self.unit)

    def as_integer(self) -> Callable[[Parameters], int]:
        raise ValueError(f"Cannot convert {self.value} to a integer.")

    def as_float(self) -> Callable[[Parameters], float]:
        if self.unit is dimensionless:
            return lambda _: self.value
        else:
            raise ValueError(f"Cannot convert {self.value} to a float.")

    def as_quantity(self, unit: Unit) -> Callable[[Parameters], float]:
        if unit.is_compatible_with(self.unit):
            result = float(Quantity(self.value, self.unit).to_unit(unit).magnitude)
            return lambda _: result
        else:
            raise ValueError(f"Cannot convert {self.value} to {unit}.")

    def as_boolean(self) -> Callable[[Parameters], bool]:
        raise ValueError(f"Cannot convert {self.value} to a boolean.")
