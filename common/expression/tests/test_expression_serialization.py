from expression import Expression
from settings_model import YAMLSerializable


def test_yaml_serialization():
    expr = Expression("1 + 2")
    assert YAMLSerializable.dump(expr) == "!Expression '1 + 2'\n"

    expr2 = YAMLSerializable.load("!Expression '1 + 2'\n")
    assert expr2 == expr
