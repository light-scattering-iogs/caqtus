from caqtus.types.expression import Expression
from caqtus.types.parameter import ParameterNamespace
from caqtus.types.variable_name import DottedVariableName

parameters = ParameterNamespace(
    [
        (
            DottedVariableName("mot_loading"),
            ParameterNamespace(
                [
                    (DottedVariableName("duration"), Expression("50 ms")),
                    (DottedVariableName("current"), Expression("2.37 A")),
                    (DottedVariableName("x_current"), Expression("0.186 A")),
                    (DottedVariableName("y_current"), Expression("0.407 A")),
                    (DottedVariableName("z_current"), Expression("-0.119 A")),
                    (DottedVariableName("blue_power"), Expression("100%")),
                    (DottedVariableName("blue_frequency"), Expression("21.7 MHz")),
                    (DottedVariableName("red_frequency"), Expression("-3.25 MHz")),
                    (DottedVariableName("red_power"), Expression("0 dB")),
                    (DottedVariableName("push_power"), Expression("0.7 mW")),
                ]
            ),
        ),
        (
            DottedVariableName("imaging"),
            ParameterNamespace(
                [
                    (DottedVariableName("power"), Expression("-18 dB")),
                    (DottedVariableName("frequency"), Expression("-18.23 MHz")),
                    (DottedVariableName("exposure"), Expression("30 ms")),
                    (DottedVariableName("x_current"), Expression("0.25 A")),
                    (DottedVariableName("y_current"), Expression("4.94 A")),
                    (DottedVariableName("z_current"), Expression("0.183 A")),
                ]
            ),
        ),
        (
            DottedVariableName("red_mot"),
            ParameterNamespace(
                [
                    (DottedVariableName("ramp_duration"), Expression("100 ms")),
                    (DottedVariableName("x_current"), Expression("0.286 A")),
                    (DottedVariableName("x_current_1"), Expression("0.27 A")),
                    (DottedVariableName("x_current_2"), Expression("0.32 A")),
                    (DottedVariableName("y_current"), Expression("0.095 A")),
                    (DottedVariableName("z_current"), Expression("0.020 A")),
                    (DottedVariableName("current"), Expression("0.8 A")),
                    (DottedVariableName("power"), Expression("-36 dB")),
                    (DottedVariableName("frequency"), Expression("-1.05 MHz")),
                    (DottedVariableName("duration"), Expression("100 ms")),
                ]
            ),
        ),
        (
            DottedVariableName("collisions"),
            ParameterNamespace(
                [
                    (DottedVariableName("power"), Expression("-17 dB")),
                    (DottedVariableName("frequency"), Expression("-18.13 MHz")),
                    (DottedVariableName("duration"), Expression("30 ms")),
                ]
            ),
        ),
        (
            DottedVariableName("tweezers"),
            ParameterNamespace(
                [
                    (DottedVariableName("loading_power"), Expression("45%")),
                    (DottedVariableName("imaging_power"), Expression("42%")),
                    (DottedVariableName("hwp_angle"), Expression("139.625°")),
                    (
                        DottedVariableName("rearrangement_duration"),
                        Expression("450 us"),
                    ),
                    (DottedVariableName("move_time"), Expression("600 us")),
                ]
            ),
        ),
        (
            DottedVariableName("repump"),
            ParameterNamespace(
                [
                    (DottedVariableName("frequency"), Expression("-16.65 MHz")),
                    (DottedVariableName("duration"), Expression("25 ms")),
                ]
            ),
        ),
        (
            DottedVariableName("cooling"),
            ParameterNamespace(
                [(DottedVariableName("frequency"), Expression("-18.10 MHz"))]
            ),
        ),
        (DottedVariableName("target_fringe_position"), Expression("0.2")),
        (DottedVariableName("kill_frequency"), Expression("+40 MHz")),
        (DottedVariableName("kill_power"), Expression("100 %")),
        (DottedVariableName("kill_time"), Expression("150 ns")),
        (DottedVariableName("kill_current"), Expression("4.96 A")),
        (
            DottedVariableName("probe"),
            ParameterNamespace(
                [
                    (DottedVariableName("frequency"), Expression("-18.215 MHz")),
                    (DottedVariableName("power"), Expression("-16 dB")),
                ]
            ),
        ),
        (DottedVariableName("perp_probe"), Expression("Disabled")),
        (DottedVariableName("parallel_probe"), Expression("Disabled")),
        (
            DottedVariableName("narrow_probe"),
            ParameterNamespace(
                [
                    (DottedVariableName("frequency"), Expression("0 MHz")),
                    (DottedVariableName("power"), Expression("0%")),
                    (DottedVariableName("frequency2"), Expression("0 MHz")),
                ]
            ),
        ),
    ]
)
