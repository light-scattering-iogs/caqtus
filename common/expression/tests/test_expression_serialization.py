from expression import Expression
from settings_model import YAMLSerializable
from util import serialization


def test_yaml_serialization():
    expr = Expression("1 + 2")
    assert YAMLSerializable.dump(expr) == "!Expression '1 + 2'\n"

    expr2 = YAMLSerializable.load("!Expression '1 + 2'\n")
    assert expr2 == expr


def test_serialization():
    expr = Expression("1 + 2")
    assert serialization.structure(serialization.unstructure(expr), Expression) == expr
