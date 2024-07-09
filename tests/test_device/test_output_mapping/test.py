import numpy as np
import pytest

from caqtus.device.sequencer.output_mapping import (
    ExpressionValue,
    OutputMapping,
    get_converter,
)
from caqtus.device.sequencer.output_mapping._output_mapping import Interpolator
from caqtus.types.expression import Expression
from caqtus.types.units import Quantity, Unit


@pytest.fixture
def variables():
    return {}


def test_expression_value(variables):
    output = ExpressionValue(Expression("1 V"))

    assert output.evaluate(variables) == Quantity(1, "V")


def test_expression_value_db(variables):
    output = ExpressionValue(Expression("0 dB"))

    evaluated = output.evaluate(variables)
    assert evaluated.units == Unit("dimensionless")
    assert evaluated.magnitude == 1


def test_expression_value_dbm(variables):
    output = ExpressionValue(Expression("0 dBm"))

    evaluated = output.evaluate(variables)
    assert evaluated.units == Unit("W")
    assert evaluated.magnitude == 1e-3


def test_serialization():
    output = ExpressionValue(Expression("1 V"))
    converter = get_converter()
    serialized = converter.unstructure(output, OutputMapping)
    assert serialized == {"type": "ExpressionValue", "value": "1 V"}

    structured = converter.structure(serialized, OutputMapping)
    assert structured == output


def test_interpolation():
    interpolator = Interpolator([(0, 0), (1, 2)], "A", "V")
    assert interpolator(Quantity(0.5, "A")) == Quantity(1, "V")
    assert interpolator(Quantity(-0.5, "A")) == Quantity(0, "V")
    assert interpolator(Quantity(1.5, "A")) == Quantity(2, "V")


def test_interpolation_db():
    interpolator = Interpolator([(0, 0), (10, 1)], "dB", "V")
    computed = interpolator((1 + 10) / 2)
    assert np.allclose(computed.to("V").magnitude, 0.5)
