import pytest

from caqtus.device.sequencer.output_mapping import (
    ExpressionValue,
    OutputMapping,
    get_converter,
)
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
