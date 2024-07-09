import numpy as np
import pytest

from caqtus.device.output_transform import (
    LinearInterpolation,
    evaluate,
    converter,
    EvaluableOutput,
)
from caqtus.device.output_transform._output_mapping import Interpolator
from caqtus.types.expression import Expression
from caqtus.types.units import Quantity, Unit


@pytest.fixture
def variables():
    return {}


def test_expression_value():
    assert evaluate(Expression("1 V"), {}) == Quantity(1, "V")


def test_expression_value_db(variables):
    evaluated = evaluate(Expression("0 dB"), {})
    assert evaluated.units == Unit("dimensionless")
    assert evaluated.magnitude == 1


def test_expression_value_dbm(variables):

    evaluated = evaluate(Expression("0 dBm"), {})
    assert evaluated.units == Unit("W")
    assert evaluated.magnitude == 1e-3


def test_interpolation():
    interpolator = Interpolator([(0, 0), (1, 2)], "A", "V")
    assert interpolator(Quantity(0.5, "A")) == Quantity(1, "V")
    assert interpolator(Quantity(-0.5, "A")) == Quantity(0, "V")
    assert interpolator(Quantity(1.5, "A")) == Quantity(2, "V")


def test_interpolation_db():
    interpolator = Interpolator([(0, 0), (10, 1)], "dB", "V")
    computed = interpolator((1 + 10) / 2)
    assert np.allclose(computed.to("V").magnitude, 0.5)


def test_linear_interpolation_serialization():
    output = LinearInterpolation(Expression("0.5 V"), ((0, 0), (1, 1)), "V", "V")

    unstructured = converter.unstructure(output, EvaluableOutput)

    structured = converter.structure(unstructured, EvaluableOutput)

    assert structured == output


def test_expression_serialization():
    output = Expression("0.5 V")

    unstructured = converter.unstructure(output, EvaluableOutput)

    structured = converter.structure(unstructured, EvaluableOutput)

    assert structured == output
