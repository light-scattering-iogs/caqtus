import pytest

from caqtus.shot_compilation import CompilationContext, CompilationError
from caqtus.shot_compilation._expression_compilation import Constant
from caqtus.types.expression import Expression
from caqtus.types.parameter import ParameterSchema
from caqtus.types.units import Quantity, units


def test_cant_add_unit():
    ctx = CompilationContext(ParameterSchema.empty(), units=units)

    with pytest.raises(CompilationError):
        Expression("MHz + 1").compile(ctx, time_dependent=False)
    with pytest.raises(CompilationError):
        Expression("1 + MHz").compile(ctx, time_dependent=False)


def test_can_add_constants():
    ctx = CompilationContext(ParameterSchema.empty(), units=units)
    assert Expression("1 + 2").compile(ctx, time_dependent=False) == Constant(3)

    assert Expression("1 MHz + 200 kHz").compile(ctx, time_dependent=False) == Constant(
        Quantity(1.2, units["MHz"])
    )

    assert Expression("1 + 0 dB").compile(ctx, time_dependent=False) == Constant(2.0)
    assert Expression("1 W + 30 dBm").compile(ctx, time_dependent=False) == Constant(
        Quantity(2.000000000000001, units["W"])
    )
    assert Expression("1 + 0.2").compile(ctx, time_dependent=False) == Constant(1.2)


def test_integer_promotion_to_float():
    ctx = CompilationContext(ParameterSchema.empty(), units=units)
    assert Expression("1.0 + -2").compile(ctx, time_dependent=False) == Constant(-1.0)


def test_can_add_number_to_dimensionless():
    ctx = CompilationContext(ParameterSchema.empty(), units=units)
    assert Expression("-1.0 + 0 dB").compile(ctx, time_dependent=False) == Constant(0.0)

    assert Expression("180 ° + 0").compile(ctx, time_dependent=False) == Constant(
        Quantity(180, units["°"])
    )


def test_cant_add_dimensionless_to_dimensioned_constants():
    ctx = CompilationContext(ParameterSchema.empty(), units=units)
    with pytest.raises(CompilationError):
        Expression("1 MHz + 1").compile(ctx, time_dependent=False)
    with pytest.raises(CompilationError):
        Expression("1 + 1 MHz").compile(ctx, time_dependent=False)
    with pytest.raises(CompilationError):
        Expression("-1.0 + 1 W").compile(ctx, time_dependent=False)
    with pytest.raises(CompilationError):
        Expression("1 W + -1.0").compile(ctx, time_dependent=False)


def test_cant_add_incompatible_units():
    ctx = CompilationContext(ParameterSchema.empty(), units=units)
    with pytest.raises(CompilationError):
        Expression("1 W + 1 mW + 1 s + 100").compile(ctx, time_dependent=False)
