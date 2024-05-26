import pytest

from caqtus.types.variable_name import (
    DottedVariableName,
    InvalidVariableNameError,
    VariableName,
)


def test_0():
    a = DottedVariableName("a")
    assert a.individual_names == (a,)


def test_1():
    x = DottedVariableName("a.b.c")
    assert x.individual_names == (
        VariableName("a"),
        VariableName("b"),
        VariableName("c"),
    )


def test_2():
    with pytest.raises(InvalidVariableNameError):
        DottedVariableName("a b")
