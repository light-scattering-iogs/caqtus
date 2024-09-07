import decimal

from caqtus.device.sequencer import converter, TimeStep
from caqtus.device.sequencer.timing import to_time_step


def test_unstructure():
    value = to_time_step("1.23")
    assert converter.unstructure(value, TimeStep) == "1.230"


def test_structure():
    value = "1.23"
    assert converter.structure(value, TimeStep) == decimal.Decimal("1.23")
