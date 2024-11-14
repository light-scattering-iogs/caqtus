import math

from caqtus.shot_compilation._evaluation import evaluate_scalar_expression
from caqtus.types.expression import Expression


def test_call():
    expr = Expression("sqrt(2)")

    result = evaluate_scalar_expression(expr, {})
    assert result == 2**0.5


def test_with_quantity():
    expr = Expression("cos(0 dB)")

    result = evaluate_scalar_expression(expr, {})
    assert result == math.cos(1)
