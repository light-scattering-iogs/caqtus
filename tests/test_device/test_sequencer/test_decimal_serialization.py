import decimal

from caqtus.device.sequencer import converter


def test_unstructure():
    value = decimal.Decimal("1.23")
    assert converter.unstructure(value) == "1.23"


def test_structure():
    value = "1.23"
    assert converter.structure(value, decimal.Decimal) == decimal.Decimal("1.23")
