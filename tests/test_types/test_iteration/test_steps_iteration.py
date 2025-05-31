from caqtus.types.expression import Expression
from caqtus.types.iteration import (
    AnalogInputRange,
    ArangeLoop,
    DigitalInput,
    ExecuteShot,
    LinspaceLoop,
    StepsConfiguration,
    TunableParameterConfig,
    VariableDeclaration,
    is_unknown,
)
from caqtus.types.iteration.steps_configurations import _converter
from caqtus.types.parameter import ParameterSchema
from caqtus.types.parameter._schema import Float, Integer, QuantityType
from caqtus.types.units import Unit
from caqtus.types.variable_name import DottedVariableName


def test_serialization(steps_configuration: StepsConfiguration):
    serialized = StepsConfiguration.dump(steps_configuration)
    expected = {
        "steps": [
            {"variable": "a", "value": "1"},
            {"variable": "c", "value": "0.0"},
            {
                "sub_steps": [{"execute": "shot"}],
                "variable": "b",
                "start": "0",
                "stop": "1",
                "num": 10,
            },
            {
                "sub_steps": [{"execute": "shot"}],
                "variable": "c",
                "start": "0",
                "stop": "1",
                "step": "0.1",
            },
            {"execute": "shot"},
        ],
        "tunable_parameters": [],
    }
    assert serialized == expected
    deserialized = StepsConfiguration.load(serialized)
    assert deserialized == steps_configuration


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
        _variable_schema={DottedVariableName("a"): QuantityType(Unit("MHz"))},
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
            DottedVariableName("var"): Integer(),
            DottedVariableName("b"): Float(),
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
        _variable_schema={DottedVariableName("a"): Float()},
    )


def test_can_serialize_tunable_analog_parameter_config():
    tunable_param = AnalogInputRange(
        min_value=Expression("0 dB"),
        max_value=Expression("1 dB"),
    )

    serialized = _converter.unstructure(tunable_param, TunableParameterConfig)
    assert serialized == {
        "AnalogInputRange": {
            "min_value": "0 dB",
            "max_value": "1 dB",
        }
    }
    deserialized = _converter.structure(
        serialized,
        TunableParameterConfig,  # pyright: ignore [reportArgumentType]
    )
    assert deserialized == tunable_param


def test_can_serialize_tunable_digital_parameter_config():
    tunable_param = DigitalInput()

    serialized = _converter.unstructure(tunable_param, TunableParameterConfig)
    assert serialized == {"DigitalInput": {}}
    deserialized = _converter.structure(
        serialized,
        TunableParameterConfig,  # pyright: ignore [reportArgumentType]
    )
    assert deserialized == tunable_param
