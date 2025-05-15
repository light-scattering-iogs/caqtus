from __future__ import annotations

import abc
import datetime
from typing import Generic, Self, assert_never, TypeAlias, Protocol

import attrs
from typing_extensions import TypeVar

from ...types.parameter import Parameter, ParameterType
from ...types.parameter._schema import Boolean, Float, Integer, QuantityType
from ...types.units import Quantity, dimensionless
import functools

T = TypeVar("T", bound=Parameter, default=Parameter, covariant=True)
PT = TypeVar("PT", bound=ParameterType, default=ParameterType, covariant=True)
NumericPT = TypeVar(
    "NumericPT",
    bound=Integer | Float | QuantityType,
    default=Integer | Float | QuantityType,
    covariant=True,
)


class CompiledExpression(Protocol[PT]):
    @property
    @abc.abstractmethod
    def dtype(self) -> PT:
        """The type the expression evaluates to."""

        raise NotImplementedError

    @abc.abstractmethod
    def cast[S: ParameterType](self, new_type: S) -> CompiledExpression[S]:
        raise NotImplementedError

    # def __add__(self, other: CompiledExpression) -> CompiledExpression:
    #     super_type = add_supertype(self.dtype, other.dtype)
    #     return Add(self.cast(super_type), other.cast(super_type))
    #
    # def __neg__(self) -> CompiledExpression[PT]:
    #     if isinstance(self.dtype, Boolean):
    #         raise TypeError(f"Cannot negate boolean {self}.")
    #     return Negate(self)
    #
    def __pos__(
        self: CompiledExpression[NumericPT],
    ) -> CompiledExpression[NumericPT]: ...


@attrs.frozen
class BooleanConstant:
    value: bool

    @property
    def dtype(self) -> Boolean:
        return Boolean()

    def cast[S: ParameterType](self, new_type: S) -> CompiledExpression[S]:
        match new_type:
            case Boolean():
                return self  # pyright: ignore [reportReturnType]
            case Integer() | Float() | QuantityType():
                raise TypeError(
                    f"Cannot cast {self} with type {self.dtype} to {new_type}."
                )
            case _:
                assert_never(self.dtype)

    def __pos__(self) -> CompiledExpression[Boolean]:
        raise TypeError(f"Cannot apply unary plus to boolean {self}.")


@attrs.frozen
class IntegerConstant:
    value: int

    @property
    def dtype(self) -> Integer:
        return Integer()

    def cast[S: ParameterType](self, new_type: S) -> CompiledExpression[S]:
        match new_type:
            case Boolean():
                raise TypeError(
                    f"Cannot cast {self} with type {self.dtype} to {new_type}."
                )
            case Integer():
                return self  # pyright: ignore [reportReturnType]
            case Float():
                return FloatConstant(
                    float(self.value)
                )  # pyright: ignore [reportReturnType]
            case QuantityType(units=units):
                if not units.is_compatible_with(dimensionless):
                    raise TypeError(
                        f"Cannot cast {self} with type {self.dtype} to {new_type}."
                    )
                return QuantityConstant(  # pyright: ignore [reportReturnType]
                    Quantity(self.value, dimensionless).to_unit(units)
                )
            case _:
                assert_never(self.dtype)

    def __pos__(self) -> IntegerConstant:
        return self


@attrs.frozen
class FloatConstant:
    value: float

    @property
    def dtype(self) -> Float:
        return Float()

    def cast[S: ParameterType](self, new_type: S) -> CompiledExpression[S]:
        match new_type:
            case Boolean() | Integer():
                raise TypeError(
                    f"Cannot cast {self} with type {self.dtype} to {new_type}."
                )
            case Float():
                return self  # pyright: ignore [reportReturnType]
            case QuantityType(units=units):
                if not units.is_compatible_with(dimensionless):
                    raise TypeError(
                        f"Cannot cast {self} with type {self.dtype} to {new_type}."
                    )
                return QuantityConstant(  # pyright: ignore [reportReturnType]
                    Quantity(self.value, dimensionless).to_unit(units)
                )
            case _:
                assert_never(self.dtype)

    def __pos__(self) -> FloatConstant:
        return self


@attrs.frozen
class QuantityConstant:
    value: Quantity[float]

    @property
    def dtype(self) -> QuantityType:
        return QuantityType(self.value.units)

    def cast[S: ParameterType](self, new_type: S) -> CompiledExpression[S]:
        match new_type:
            case Boolean() | Integer():
                raise TypeError(
                    f"Cannot cast {self} with type {self.dtype} to {new_type}."
                )
            case Float():
                if not self.value.units.is_compatible_with(dimensionless):
                    raise TypeError(
                        f"Cannot cast {self} with type {self.dtype} to {new_type}."
                    )
                return FloatConstant(  # pyright: ignore [reportReturnType]
                    self.value.to_unit(dimensionless).magnitude
                )
            case QuantityType(units=target_units):
                if not self.value.units.is_compatible_with(target_units):
                    raise TypeError(
                        f"Cannot cast {self} with type {self.dtype} to {new_type}."
                    )
                return QuantityConstant(  # pyright: ignore [reportReturnType]
                    self.value.to_unit(target_units)
                )
            case _:
                assert_never(self.dtype)

    def __pos__(self) -> QuantityConstant:
        return self


type Constant = BooleanConstant | IntegerConstant | FloatConstant | QuantityConstant


def f() -> Constant:
    raise NotImplementedError


b: CompiledExpression = f()


def add_supertype(
    lhs_type: ParameterType,
    rhs_type: ParameterType,
) -> ParameterType:
    raise NotImplementedError


def add(lhs: _CompiledExpression, rhs: _CompiledExpression) -> _CompiledExpression:
    if isinstance(lhs.dtype, Boolean):
        raise TypeError(f"Cannot add boolean {lhs} to {rhs}.")
    if isinstance(rhs.dtype, Boolean):
        raise TypeError(f"Cannot add {lhs} to boolean {rhs}.")
    match lhs.dtype:
        case Integer() | Float():
            match rhs.dtype:
                case Integer() | Float():
                    return optimized_add(lhs, rhs)
                case QuantityType(units=units):
                    if not units.is_compatible_with(dimensionless):
                        raise TypeError(
                            f"Cannot add dimensionless {lhs} to {rhs} with "
                            f'units "{units:~}"'
                        )
                    return optimized_add(lhs, rhs.cast(Float))
                case _:
                    assert_never(rhs)
        case QuantityType(units=lhs_units):
            match rhs.dtype:
                case Integer() | Float():
                    if not lhs_units.is_compatible_with(dimensionless):
                        raise TypeError(
                            f'Cannot add left side with units "{lhs_units:~}" and '
                            f"dimensionless right side"
                        )
                    return optimized_add(lhs.cast(Float), rhs)
                case QuantityType(units=rhs_units):
                    if not lhs_units.is_compatible_with(rhs_units):
                        raise TypeError(
                            f'Cannot add left side with units "{lhs_units}" and '
                            f'right side with units "{rhs_units}"'
                        )
                    return optimized_add(lhs, rhs.cast(QuantityType(lhs_units)))
                case _:
                    assert_never(rhs)
        case _:
            assert_never(lhs)


def optimized_add(
    lhs: _CompiledExpression, rhs: _CompiledExpression
) -> _CompiledExpression:
    if isinstance(lhs, Constant) and isinstance(rhs, Constant):
        result = lhs.value + rhs.value
        assert not isinstance(result, datetime.datetime)
        return Constant(result)
    else:
        return Add(lhs, rhs)


@attrs.frozen
class VariableParameter(CompiledExpression, Generic[PT]):
    type_: PT
    name: str

    def __str__(self):
        return f"{self.name}"

    def __pos__(self) -> Self:
        if isinstance(self.type_, Boolean):
            raise TypeError(f"Cannot apply unary plus to boolean parameter {self}.")
        return self

    @property
    def dtype(self) -> ParameterType:
        return self.type_


@attrs.frozen
class Negate[T]:
    operand: T

    @property
    def dtype[
        PT: ParameterType
    ](self: Negate[CompiledExpression[PT]],) -> PT:
        return self.operand.dtype

    def cast[
        S: ParameterType
    ](self: Negate[CompiledExpression], new_type: S) -> CompiledExpression[S]:
        v = self.operand.cast(new_type)
        r = Negate(v)
        return r

    def __neg__(self) -> T:
        return self.operand

    def __pos__(self) -> Self:
        return self

    def __add__(self, other: CompiledExpression[PT]) -> CompiledExpression[PT]:
        raise NotImplementedError


@attrs.frozen
class Add(CompiledExpression, Generic[PT]):
    lhs: _CompiledExpression[PT]
    rhs: _CompiledExpression[PT]

    @functools.cached_property
    def dtype(  # pyright: ignore [reportIncompatibleMethodOverride]
        self,
    ) -> ParameterType:
        assert self.lhs.dtype == self.rhs.dtype
        return self.lhs.dtype


_CompiledExpression: TypeAlias = (
    Constant[PT] | VariableParameter[PT] | Negate[PT] | Add[PT]
)
