from typing import assert_never

import cattrs
from ._user_input_widget import InputType, AnalogRange, DigitalInput
from caqtus.types.units import configure_units


def configure_input_type(converter: cattrs.Converter) -> None:
    """Configure a `cattrs.Converter` to be able to handle `InputType` instances."""

    configure_units(converter)

    analog_unstructure = converter.get_unstructure_hook(AnalogRange)
    digital_unstructure = converter.get_unstructure_hook(DigitalInput)

    def unstructure_input_type(t: InputType) -> dict:
        match t:
            case AnalogRange():
                return {"AnalogRange": analog_unstructure(t)}
            case DigitalInput():
                return {"DigitalInput": digital_unstructure(t)}
            case _:
                assert_never(t)

    converter.register_unstructure_hook_func(
        lambda t: t is InputType, unstructure_input_type
    )

    analog_structure = converter.get_structure_hook(AnalogRange)
    digital_structure = converter.get_structure_hook(DigitalInput)

    def structure_input_type(data, _) -> InputType:
        match data:
            case {"AnalogRange": analog_data}:
                return analog_structure(analog_data, None)
            case {"DigitalInput": digital_data}:
                return digital_structure(digital_data, None)
            case _:
                raise ValueError(f"Cannot structure data as InputType: {data}")

    converter.register_structure_hook_func(
        lambda t: t is InputType, structure_input_type
    )
