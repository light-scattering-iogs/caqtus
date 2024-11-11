import pytest

from caqtus.shot_compilation._evaluation import (
    evaluate_scalar_expression,
    UndefinedParameterError,
)
from caqtus.shot_compilation._evaluation._constants import CONSTANTS
from caqtus.types.expression import Expression
from caqtus.types.variable_name import DottedVariableName


def test_variable_evaluation():
    expr = Expression("a")
    parameters = {DottedVariableName("a"): 12}

    result = evaluate_scalar_expression(expr, parameters)
    assert isinstance(result, int)
    assert result == 12


def test_dotted_parameter():
    expr = Expression("a.b")
    parameters = {DottedVariableName("a.b"): 12}

    result = evaluate_scalar_expression(expr, parameters)
    assert isinstance(result, int)
    assert result == 12


def test_undefined_parameter():
    expr = Expression("a")
    parameters = {}

    with pytest.raises(UndefinedParameterError):
        evaluate_scalar_expression(expr, parameters)


def test_constant():
    expr = Expression("pi")
    parameters = {}

    result = evaluate_scalar_expression(expr, parameters)
    assert result == CONSTANTS["pi"]
