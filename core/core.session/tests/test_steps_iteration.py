from core.session.sequence.iteration_configuration import (
    StepsConfiguration,
    ExecuteShot,
    VariableDeclaration,
    LinspaceLoop,
    ArangeLoop,
)
from core.types.expression import Expression
from core.types.variable_name import DottedVariableName


def test_serialization():
    step_configuration = StepsConfiguration(
        steps=[
            VariableDeclaration(
                variable=DottedVariableName("a"), value=Expression("1")
            ),
            LinspaceLoop(
                variable=DottedVariableName("b"),
                start=Expression("0"),
                stop=Expression("1"),
                num=10,
                sub_steps=[
                    ExecuteShot(),
                ],
            ),
            ArangeLoop(
                variable=DottedVariableName("c"),
                start=Expression("0"),
                stop=Expression("1"),
                step=Expression("0.1"),
                sub_steps=[
                    ExecuteShot(),
                ],
            ),
            ExecuteShot(),
        ],
    )
    print(StepsConfiguration.dump(step_configuration))

    assert step_configuration == StepsConfiguration.load(
        StepsConfiguration.dump(step_configuration)
    )
