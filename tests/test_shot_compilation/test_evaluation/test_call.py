import pytest

from caqtus.shot_compilation._evaluation import evaluate_scalar_expression
from caqtus.types.expression import Expression
from caqtus.types.units import Quantity, Unit
from caqtus.types.variable_name import DottedVariableName


def test_call():
    expr = Expression("sqrt(2)")

    result = evaluate_scalar_expression(expr, {})
    assert result == 2**0.5


def test_with_quantity():
    expr = Expression("cos(90°)")

    result = evaluate_scalar_expression(expr, {})
    assert result == pytest.approx(0)


def test_rad():
    expr = Expression("cos(2 * pi * t * freq)")

    parameters = {
        DottedVariableName("t"): Quantity(0.5, Unit("s")),
        DottedVariableName("freq"): Quantity(2, Unit("Hz")),
    }

    result = evaluate_scalar_expression(expr, parameters)
    assert result == pytest.approx(1)
