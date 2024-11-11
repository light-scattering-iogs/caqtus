from caqtus.shot_compilation._evaluation import evaluate_scalar_expression
from caqtus.types.expression import Expression
from caqtus.types.variable_name import DottedVariableName


def test_add():
    expr = Expression("a + b")
    parameters = {DottedVariableName("a"): 12, DottedVariableName("b"): 13}

    result = evaluate_scalar_expression(expr, parameters)
    assert result == 25


def test_subtract():
    expr = Expression("a - b")
    parameters = {DottedVariableName("a"): 12, DottedVariableName("b"): 13}

    result = evaluate_scalar_expression(expr, parameters)
    assert result == -1


def test_multiply():
    expr = Expression("a * b")
    parameters = {DottedVariableName("a"): 12, DottedVariableName("b"): 13}

    result = evaluate_scalar_expression(expr, parameters)
    assert result == 156


def test_divide():
    expr = Expression("a / b")
    parameters = {DottedVariableName("a"): 12, DottedVariableName("b"): 13}

    result = evaluate_scalar_expression(expr, parameters)
    assert result == 12 / 13


def test_power():
    expr = Expression("a ** b")
    parameters = {DottedVariableName("a"): 2, DottedVariableName("b"): 3}

    result = evaluate_scalar_expression(expr, parameters)
    assert result == 8
