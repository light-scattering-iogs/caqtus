import pickle

from caqtus.types.expression import Expression
from caqtus.types.parameter import ParameterNamespace
from caqtus.types.units import ureg
from caqtus.types.variable_name import DottedVariableName
from caqtus.utils import serialization


def test_0():
    namespace = ParameterNamespace.from_mapping(
        {
            "a": Expression("1"),
            "b": {
                "c": Expression("2"),
                "d": Expression("3"),
            },
        }
    )
    assert list(namespace.flatten()) == [
        (DottedVariableName("a"), Expression("1")),
        (DottedVariableName("b.c"), Expression("2")),
        (DottedVariableName("b.d"), Expression("3")),
    ]


def test_1():
    namespace = ParameterNamespace.from_mapping(
        {
            "a": Expression("1"),
            "b": {
                "c": Expression("2"),
                "d": Expression("3"),
            },
        }
    )
    assert list(namespace.items()) == [
        (DottedVariableName("a"), Expression("1")),
        (
            DottedVariableName("b"),
            ParameterNamespace(
                [
                    (DottedVariableName("c"), Expression("2")),
                    (DottedVariableName("d"), Expression("3")),
                ]
            ),
        ),
    ]


def test_serialization():
    namespace = ParameterNamespace.from_mapping(
        {
            "a": Expression("1"),
            "b": {
                "c": Expression("2"),
                "d": Expression("3"),
            },
        }
    )
    unstructured = serialization.unstructure(namespace)
    assert serialization.structure(unstructured, ParameterNamespace) == namespace


def test_get():
    namespace = ParameterNamespace.from_mapping(
        {
            "a.b": Expression("1"),
            "a": {"b": Expression("2")},
        }
    )
    assert namespace.get(DottedVariableName("a.b")) == Expression("2")


def test_evaluation():
    namespace = ParameterNamespace.from_mapping(
        {"a": Expression("1"), "b": Expression("2 * a")}
    )
    values = namespace.evaluate()
    assert values == {DottedVariableName("a"): 1, DottedVariableName("b"): 2}


def test_evaluation_units():
    namespace = ParameterNamespace.from_mapping({"a": Expression("1 kHz")})
    values = namespace.evaluate()
    assert values == {DottedVariableName("a"): 1 * ureg.kHz}


def test_replace():
    namespace = ParameterNamespace.from_mapping({"a.b": Expression("1")})
    namespace.replace(DottedVariableName("a.b"), Expression("2"))
    assert namespace.evaluate()[DottedVariableName("a.b")] == 2


def test_replace_():
    namespace = ParameterNamespace.from_mapping({"a": {"b": Expression("1")}})
    namespace.replace(DottedVariableName("a.b"), Expression("2"))
    assert namespace.evaluate()[DottedVariableName("a.b")] == 2


def test_pickle():
    namespace = ParameterNamespace(
        [
            (
                DottedVariableName("mot_loading"),
                ParameterNamespace(
                    [
                        (DottedVariableName("duration"), Expression("100 ms")),
                        (DottedVariableName("current"), Expression("2.119 A")),
                        (DottedVariableName("x_current"), Expression("0.119 A")),
                        (DottedVariableName("y_current"), Expression("0.331 A")),
                        (DottedVariableName("z_current"), Expression("-0.085 A")),
                        (DottedVariableName("blue_power"), Expression("100%")),
                        (
                            DottedVariableName("blue_frequency"),
                            Expression("18.983 MHz"),
                        ),
                        (DottedVariableName("red_frequency"), Expression("-3.254 MHz")),
                        (DottedVariableName("red_power"), Expression("0 dB")),
                        (DottedVariableName("push_power"), Expression("0.7 mW")),
                    ]
                ),
            ),
            (
                DottedVariableName("imaging"),
                ParameterNamespace(
                    [
                        (DottedVariableName("power"), Expression("-28 dB")),
                        (DottedVariableName("frequency"), Expression("-18.076 MHz")),
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
                        (DottedVariableName("ramp_duration"), Expression("80 ms")),
                        (DottedVariableName("x_current"), Expression("0.27 A")),
                        (DottedVariableName("x_current_1"), Expression("0.27 A")),
                        (DottedVariableName("x_current_2"), Expression("0.29 A")),
                        (DottedVariableName("y_current"), Expression("0.105 A")),
                        (DottedVariableName("z_current"), Expression("0.014 A")),
                        (DottedVariableName("current"), Expression("1 A")),
                        (DottedVariableName("power"), Expression("-36 dB")),
                        (DottedVariableName("frequency"), Expression("-1 MHz")),
                        (DottedVariableName("duration"), Expression("80 ms")),
                    ]
                ),
            ),
            (
                DottedVariableName("collisions"),
                ParameterNamespace(
                    [
                        (DottedVariableName("power"), Expression("-21 dB")),
                        (DottedVariableName("frequency"), Expression("-18.08 MHz")),
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
                        (DottedVariableName("hwp_angle"), Expression("139.75°")),
                        (
                            DottedVariableName("rearrangement_duration"),
                            Expression("400 us"),
                        ),
                        (DottedVariableName("move_time"), Expression("600 us")),
                    ]
                ),
            ),
            (
                DottedVariableName("probe"),
                ParameterNamespace(
                    [
                        (DottedVariableName("frequency"), Expression("-18 MHz")),
                        (DottedVariableName("power"), Expression("-30 dB")),
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
                    [(DottedVariableName("frequency"), Expression("-18.01 MHz"))]
                ),
            ),
            (DottedVariableName("piezos_voltage"), Expression("38.9 V")),
            (DottedVariableName("kill_frequency"), Expression("+40 MHz")),
            (DottedVariableName("kill_power"), Expression("100 %")),
            (DottedVariableName("kill_time"), Expression("150 ns")),
            (DottedVariableName("kill_current"), Expression("4.96 A")),
        ]
    )
    s = pickle.dumps(namespace)
