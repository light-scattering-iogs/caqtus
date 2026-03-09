from caqtus.types.expression import Expression
from caqtus.types.iteration import (
    StepsConfiguration,
    VariableDeclaration,
    ArangeLoop,
    ExecuteShot,
)
from caqtus.types.variable_name import DottedVariableName

iterations = StepsConfiguration(
    steps=[
        VariableDeclaration(
            variable=DottedVariableName("kill_time"), value=Expression("1 us")
        ),
        VariableDeclaration(
            variable=DottedVariableName("tof_duration"), value=Expression("30 us")
        ),
        VariableDeclaration(
            variable=DottedVariableName("initial_frequency"),
            value=Expression("-0.9 MHz"),
        ),
        VariableDeclaration(
            variable=DottedVariableName("final_frequency"),
            value=Expression("-0.29 MHz"),
        ),
        VariableDeclaration(
            variable=DottedVariableName("duration_741"), value=Expression("250 us")
        ),
        VariableDeclaration(
            variable=DottedVariableName("cooling_duration"), value=Expression("50 ms")
        ),
        VariableDeclaration(
            variable=DottedVariableName("cooling_741_power"), value=Expression("-30 dB")
        ),
        VariableDeclaration(
            variable=DottedVariableName("frequency_741"), value=Expression("0 MHz")
        ),
        ArangeLoop(
            sub_steps=[
                ArangeLoop(
                    sub_steps=[ExecuteShot()],
                    variable=DottedVariableName("duration_741"),
                    start=Expression("0 us"),
                    stop=Expression("15 us"),
                    step=Expression("0.4 us"),
                )
            ],
            variable=DottedVariableName("rep"),
            start=Expression("0"),
            stop=Expression("10"),
            step=Expression("1"),
        ),
    ]
)
