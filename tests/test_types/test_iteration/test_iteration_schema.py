from caqtus.types.expression import Expression
from caqtus.types.iteration import LinspaceLoop, ExecuteShot, VariableDeclaration
from caqtus.types.iteration._iteration_schema import (
    compute_iteration_schema,
    IteratedParameter,
)
from caqtus.types.parameter._schema import Float
from caqtus.types.variable_name import DottedVariableName
import pytest


def test_correct_schema_float_loop():
    steps = [
        LinspaceLoop(
            variable=DottedVariableName("a"),
            start=Expression("0.0"),
            stop=Expression("1.0"),
            num=10,
            sub_steps=[
                ExecuteShot(),
            ],
        ),
    ]

    schema = compute_iteration_schema(steps, {})
    assert schema == {DottedVariableName("a"): IteratedParameter(1, Float())}


def test_error_on_invalid_redefinition():
    steps = [
        LinspaceLoop(
            variable=DottedVariableName("a"),
            start=Expression("0 dB"),
            stop=Expression("1 dB"),
            num=10,
            sub_steps=[
                ExecuteShot(),
            ],
        ),
        VariableDeclaration(DottedVariableName("a"), Expression("12 MHz")),
    ]

    with pytest.raises(TypeError):
        schema = compute_iteration_schema(steps, {})
