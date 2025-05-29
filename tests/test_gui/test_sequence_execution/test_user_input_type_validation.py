from caqtus.types.units import Unit
from caqtus.utils.serialization import copy_converter
from caqtus.gui._sequence_execution import (
    AnalogRange,
    DigitalInput,
    InputType,
    configure_input_type,
)


def test_can_serialize_analog_input_range():
    analog_range = AnalogRange(0.0, 10.0, Unit("V"))

    converter = copy_converter()
    configure_input_type(converter)
    serialized = converter.unstructure(analog_range, InputType)
    assert serialized == {
        "AnalogRange": {"minimum": 0.0, "maximum": 10.0, "unit": "volt"}
    }

    reconstructed = converter.structure(
        serialized,
        InputType,  # pyright: ignore [reportArgumentType]
    )
    assert reconstructed == analog_range


def test_can_serialize_digital_input():
    digital_input = DigitalInput()

    converter = copy_converter()
    configure_input_type(converter)
    serialized = converter.unstructure(digital_input, InputType)
    assert serialized == {"DigitalInput": {}}

    reconstructed = converter.structure(
        serialized,
        InputType,  # pyright: ignore [reportArgumentType]
    )
    assert reconstructed == digital_input
