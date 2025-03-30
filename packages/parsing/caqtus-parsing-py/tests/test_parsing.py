from caqtus_parsing import ParseNode, parse


def test_successfully_parse_integer():
    assert parse("123") == ParseNode.Integer(123)


def test_successfully_parse_float():
    assert parse("12e-3") == ParseNode.Float(12e-3)


def test_successfully_parse_identifier():
    assert parse("a.b.c") == ParseNode.Identifier("a.b.c")


def test_successfully_parse_quantity():
    assert parse("123.45 m") == ParseNode.Quantity(123.45, "m")


def test_repr():
    assert repr(ParseNode.Integer(123)) == "Integer(123)"
    assert (
        repr(ParseNode.Add(ParseNode.Integer(123), ParseNode.Integer(456)))
        == "Add(Integer(123), Integer(456))"
    )
    assert (
        repr(ParseNode.Subtract(ParseNode.Integer(123), ParseNode.Integer(456)))
        == "Subtract(Integer(123), Integer(456))"
    )


def test_can_parse_sum():
    assert parse("123 + 456") == ParseNode.Add(
        ParseNode.Integer(123), ParseNode.Integer(456)
    )


def test_can_pickle():
    import pickle

    original = ParseNode.Add(ParseNode.Integer(123), ParseNode.Integer(456))
    pickled = pickle.dumps(original)
    unpickled = pickle.loads(pickled)
    assert original == unpickled
