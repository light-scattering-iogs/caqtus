from caqtus.shot_compilation._evaluation import evaluate_scalar_expression
from caqtus.types.expression import Expression
from caqtus.types.variable_name import DottedVariableName


def test_plus_operator():
    expr = Expression("+a")
    parameters = {DottedVariableName("a"): 12}

    result = evaluate_scalar_expression(expr, parameters)
    assert result == 12


def test_minus_operator():
    expr = Expression("-mot.detuning")
    parameters = {DottedVariableName("mot.detuning"): 12}

    result = evaluate_scalar_expression(expr, parameters)
    assert result == -12
