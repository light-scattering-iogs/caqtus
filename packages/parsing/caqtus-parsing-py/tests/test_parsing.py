from caqtus_parsing import ParseNode, parse


def test_successfully_parse_integer():
    assert parse("123") == ParseNode.Integer(123)


def test_successfully_parse_float():
    assert parse("12e-3") == ParseNode.Float(12e-3)


def test_successfully_parse_identifier():
    assert parse("a.b.c") == ParseNode.Identifier("a.b.c")
