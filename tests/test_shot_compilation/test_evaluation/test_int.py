from caqtus.shot_compilation._evaluation import evaluate_scalar_expression
from caqtus.types.expression import Expression


def test_evaluate_integer():
    expr = Expression("12")

    result = evaluate_scalar_expression(expr, {})
    assert isinstance(result, int)
    assert result == 12


def test_evaluate_float():
    expr = Expression("-12.5")

    result = evaluate_scalar_expression(expr, {})
    assert isinstance(result, float)
    assert result == -12.5
