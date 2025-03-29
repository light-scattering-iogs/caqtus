from caqtus_parsing import parse, ParseNode


def test_successfully_parse_integer():
    assert parse("123") == ParseNode.Integer(123)
