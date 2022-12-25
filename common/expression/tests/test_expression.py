import numpy as np
import pytest

from expression import Expression
from expression import __version__


def test_version():
    assert __version__ == "0.1.0"


def test_simple_evaluation():
    assert Expression("a + b").evaluate({"a": 1, "b": 2}) == 3


def test_builtins():
    assert Expression("sin(pi / 4)").evaluate({}) == np.sin(np.pi / 4)
    with pytest.raises(NameError):
        Expression("sin(0)").evaluate({"sin": np.cos})
    with pytest.raises(NameError):
        Expression("0").evaluate({"sin": None})


def test_numpy():
    assert np.alltrue(
        Expression("tanh([0.5, 0.1])").evaluate({}) == np.tanh([0.5, 0.1])
    )


def test_upstream_variables():
    assert Expression("a + b").upstream_variables == {"a", "b"}
    assert Expression("sin(x)").upstream_variables == {"x"}
