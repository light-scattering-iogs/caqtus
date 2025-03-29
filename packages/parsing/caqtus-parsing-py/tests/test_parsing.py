from caqtus_parsing import parse, AST

def test_successfully_parse_integer():
    assert parse("123") == AST.Integer(123)
