import numpy as np
import pytest

from caqtus.device.output_transform import (
    LinearInterpolation,
    evaluate,
    converter,
    EvaluableOutput,
)
from caqtus.device.output_transform._output_mapping import interpolate
from caqtus.types.expression import Expression
from caqtus.types.units import Quantity, Unit, VOLT, dimensionless, AMPERE, DECIBEL


@pytest.fixture
def variables():
    return {}


def test_expression_value():
    assert evaluate(Expression("1 V"), {}) == 1 * VOLT


def test_expression_value_db(variables):
    evaluated = evaluate(Expression("0 dB"), {})
    assert isinstance(evaluated, float)
    assert evaluated == 1


def test_expression_value_dbm(variables):

    evaluated = evaluate(Expression("0 dBm"), {})
    assert isinstance(evaluated, Quantity)
    assert evaluated.units == Unit("W")
    assert evaluated.magnitude == 1e-3


def test_interpolation():
    input_values = Quantity([0, 1], AMPERE)
    output_values = Quantity([0, 2], VOLT)
    assert interpolate(Quantity(0.5, AMPERE), input_values, output_values) == Quantity(
        1, VOLT
    )
    assert interpolate(Quantity(-0.5, AMPERE), input_values, output_values) == Quantity(
        0, VOLT
    )
    assert interpolate(Quantity(1.5, AMPERE), input_values, output_values) == Quantity(
        2, VOLT
    )


def test_interpolation_db():
    input_values = Quantity([0, 10], DECIBEL)
    output_values = Quantity([0, 1], VOLT)
    computed = interpolate(
        Quantity((1 + 10) / 2, dimensionless), input_values, output_values
    )
    assert isinstance(computed, Quantity)
    assert np.allclose(computed.to(VOLT).magnitude, 0.5)


def test_linear_interpolation_serialization():
    output = LinearInterpolation(Expression("0.5 V"), ((0, 0), (1, 1)), "V", "V")

    unstructured = converter.unstructure(output, EvaluableOutput)
    assert unstructured == {
        "input_": "0.5 V",
        "measured_data_points": ((0, 0), (1, 1)),
        "input_points_unit": "V",
        "output_points_unit": "V",
        "type": "LinearInterpolation",
    }
    structured = converter.structure(unstructured, EvaluableOutput)  # type: ignore

    assert structured == output


def test_expression_serialization():
    output = Expression("0.5 V")

    unstructured = converter.unstructure(output, EvaluableOutput)

    structured = converter.structure(unstructured, EvaluableOutput)  # type: ignore

    assert structured == output
