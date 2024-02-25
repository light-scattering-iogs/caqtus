from core.session import ParameterNamespace
from core.types.expression import Expression
from core.types.variable_name import DottedVariableName
from util import serialization


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
