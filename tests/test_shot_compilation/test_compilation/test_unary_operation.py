import pytest

from caqtus.shot_compilation import CompilationContext, CompilationError
from caqtus.shot_compilation._expression_compilation import Literal
from caqtus.types.expression import Expression
from caqtus.types.parameter import ParameterSchema
from caqtus.types.units import units


def test_applying_unary_operator_to_unit_raise_error():
    expr = Expression("-MHz")

    ctx = CompilationContext(ParameterSchema.empty(), units=units)

    with pytest.raises(CompilationError):
        expr.compile(ctx, False)


def test_negating_float_returns_float():
    expr = Expression("-1.0")
    ctx = CompilationContext(ParameterSchema.empty(), units=units)

    compiled = expr.compile(ctx, False)

    assert compiled == Literal(-1.0)


def test_negating_integer_returns_integer():
    expr = Expression("-1")
    ctx = CompilationContext(ParameterSchema.empty(), units=units)

    compiled = expr.compile(ctx, False)

    assert compiled == Literal(-1)


def test_multiple_literal_negations_are_swallowed():
    expr = Expression("----1")
    ctx = CompilationContext(ParameterSchema.empty(), units=units)

    compiled = expr.compile(ctx, False)

    assert compiled == Literal(1)


def test_negative_quantity_returns_negative_quantity():
    expr = Expression("-1.0 MHz")
    ctx = CompilationContext(ParameterSchema.empty(), units=units)

    compiled = expr.compile(ctx, False)

    assert compiled == Literal(-1.0 * units["MHz"])
