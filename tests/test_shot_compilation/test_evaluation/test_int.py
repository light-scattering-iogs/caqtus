from caqtus.shot_compilation._evaluation import evaluate_scalar_expression
from caqtus.types.expression import Expression


def test_evaluate_integer():
    expr = Expression("12")

    result = evaluate_scalar_expression(expr, {})
    assert result == 12
