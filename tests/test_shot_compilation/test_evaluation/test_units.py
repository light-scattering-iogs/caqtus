import pytest

from caqtus.shot_compilation._evaluation import evaluate_scalar_expression
from caqtus.types.expression import Expression
from caqtus.types.recoverable_exceptions import EvaluationError
from caqtus.types.units import Unit, Quantity


def test_units():
    expr = Expression("12 MHz")
    parameters = {}

    result = evaluate_scalar_expression(expr, parameters)
    assert result == Quantity(12, Unit("MHz"))


def test_undefined_units():
    expr = Expression("12 foo")
    parameters = {}

    with pytest.raises(EvaluationError):
        evaluate_scalar_expression(expr, parameters)


def test_fractional_units():
    expr = Expression("12.5 MHz / V")
    parameters = {}

    result = evaluate_scalar_expression(expr, parameters)
    assert result == Quantity(12.5, Unit("MHz/V"))
