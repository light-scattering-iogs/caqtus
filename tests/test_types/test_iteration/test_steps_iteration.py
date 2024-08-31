from caqtus.types.iteration import (
    StepsConfiguration,
    LinspaceLoop,
    ExecuteShot,
)
from caqtus.types.expression import Expression
from caqtus.types.variable_name import DottedVariableName
from tests.fixtures.steps_iteration import steps_configuration


def test_serialization(steps_configuration: StepsConfiguration):
    assert steps_configuration == StepsConfiguration.load(
        StepsConfiguration.dump(steps_configuration)
    )


def test_number():
    steps = StepsConfiguration(
        steps=[
            LinspaceLoop(
                variable=DottedVariableName("a"),
                start=Expression("0"),
                stop=Expression("1"),
                num=10,
                sub_steps=[
                    ExecuteShot(),
                ],
            ),
        ]
    )
    assert steps.expected_number_shots() == 10


def test_parameter_names():
    steps = StepsConfiguration(
        steps=[
            LinspaceLoop(
                variable=DottedVariableName("a"),
                start=Expression("0"),
                stop=Expression("1"),
                num=10,
                sub_steps=[
                    ExecuteShot(),
                ],
            ),
        ]
    )
    assert steps.get_parameter_names() == {DottedVariableName("a")}
