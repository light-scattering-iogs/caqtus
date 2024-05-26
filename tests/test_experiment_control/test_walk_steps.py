from caqtus.experiment_control.sequence_runner import walk_steps
from caqtus.experiment_control.sequence_runner.step_context import StepContext
from caqtus.types.iteration import (
    ArangeLoop,
    ExecuteShot,
    VariableDeclaration,
)
from caqtus.types.expression import Expression
from caqtus.types.variable_name import DottedVariableName


def test_0():
    steps = [
        ArangeLoop(
            start=Expression("0"),
            stop=Expression("10"),
            step=Expression("1"),
            variable=DottedVariableName("x"),
            sub_steps=[ExecuteShot()],
        )
    ]
    counter = 0
    for namespace in walk_steps(steps, StepContext()):
        assert namespace.variables["x"] == counter
        counter += 1


def test_1():
    steps = [
        ArangeLoop(
            start=Expression("0"),
            stop=Expression("10"),
            step=Expression("1"),
            variable=DottedVariableName("x"),
            sub_steps=[
                VariableDeclaration(DottedVariableName("y"), Expression("2 * x")),
                ExecuteShot(),
            ],
        )
    ]
    counter = 0
    for namespace in walk_steps(steps, StepContext()):
        assert namespace.variables["y"] == 2 * counter
        counter += 1


def test_2():
    steps = [
        ArangeLoop(
            start=Expression("0"),
            stop=Expression("10"),
            step=Expression("1"),
            variable=DottedVariableName("x"),
            sub_steps=[
                ExecuteShot(),
            ],
        ),
        ArangeLoop(
            start=Expression("x"),
            stop=Expression("x + 10"),
            step=Expression("1"),
            variable=DottedVariableName("x"),
            sub_steps=[
                ExecuteShot(),
            ],
        ),
    ]
    expected_values = [
        0,
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
    ]
    for expected, namespace in zip(expected_values, walk_steps(steps, StepContext())):
        assert namespace.variables["x"] == expected
