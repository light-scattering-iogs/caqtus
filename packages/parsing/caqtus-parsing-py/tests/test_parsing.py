from caqtus_parsing import (
    BinaryOperation,
    Call,
    Float,
    Identifier,
    Integer,
    Minus,
    Plus,
    Quantity,
    Times,
    parse,
)


def test_successfully_parse_integer():
    assert parse("123") == Integer(123)


def test_successfully_parse_float():
    assert parse("12e-3") == Float(12e-3)


def test_successfully_parse_identifier():
    assert parse("a.b.c") == Identifier("a.b.c")


def test_successfully_parse_quantity():
    assert parse("123.45 m") == Quantity(123.45, "m")


def test_repr():
    assert repr(Integer(123)) == "Integer(123)"
    assert (
        repr(BinaryOperation(Plus, Integer(123), Integer(456)))
        == "BinaryOperation(Plus, Integer(123), Integer(456))"
    )
    assert (
        repr(BinaryOperation(Minus, Integer(123), Integer(456)))
        == "BinaryOperation(Minus, Integer(123), Integer(456))"
    )


def test_can_parse_sum():
    assert parse("123 + 456") == BinaryOperation(Plus, Integer(123), Integer(456))


def test_can_parse_call():
    assert parse("sin(omega * t)") == Call(
        "sin", [BinaryOperation(Times, Identifier("omega"), Identifier("t"))]
    )
