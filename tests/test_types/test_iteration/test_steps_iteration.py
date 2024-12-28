from caqtus.types.expression import Expression
from caqtus.types.iteration import (
    StepsConfiguration,
    LinspaceLoop,
    ExecuteShot,
    ArangeLoop,
    is_unknown,
    VariableDeclaration,
)
from caqtus.types.parameter import ParameterSchema
from caqtus.types.units import Unit
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


def test_issue_35():
    steps = StepsConfiguration(
        steps=[
            ArangeLoop(
                variable=DottedVariableName("a"),
                start=Expression("0"),
                stop=Expression("1 us"),
                step=Expression("0.1 us"),
                sub_steps=[
                    ExecuteShot(),
                ],
            ),
        ]
    )
    assert is_unknown(steps.expected_number_shots())


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


def test_parameter_schema_no_constants():
    steps = StepsConfiguration(
        steps=[
            LinspaceLoop(
                variable=DottedVariableName("a"),
                start=Expression("0 MHz"),
                stop=Expression("10 kHz"),
                num=10,
                sub_steps=[
                    ExecuteShot(),
                ],
            ),
        ]
    )
    assert steps.get_parameter_schema({}) == ParameterSchema(
        _constant_schema={},
        _variable_schema={
            DottedVariableName("a"): ParameterSchema.Quantity(Unit("MHz"))
        },
    )


def test_parameter_schema_constants():
    steps = StepsConfiguration(
        steps=[
            VariableDeclaration(DottedVariableName("var"), Expression("2 * a")),
            LinspaceLoop(
                variable=DottedVariableName("b"),
                start=Expression("0"),
                stop=Expression("1"),
                num=10,
                sub_steps=[
                    ExecuteShot(),
                ],
            ),
        ]
    )
    assert steps.get_parameter_schema({DottedVariableName("a"): 0}) == ParameterSchema(
        _constant_schema={DottedVariableName("a"): 0},
        _variable_schema={
            DottedVariableName("var"): ParameterSchema.Integer(),
            DottedVariableName("b"): ParameterSchema.Float(),
        },
    )


def test_parameter_schema_constant_redefinition():
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
    assert steps.get_parameter_schema({DottedVariableName("a"): 0}) == ParameterSchema(
        _constant_schema={},
        _variable_schema={DottedVariableName("a"): ParameterSchema.Float()},
    )
