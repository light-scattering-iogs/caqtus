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
