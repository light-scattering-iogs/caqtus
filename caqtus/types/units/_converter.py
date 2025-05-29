import cattrs
from ._units import Unit


def configure_units(converter: cattrs.Converter) -> None:
    """Configure a converter to be able to handle `:class:caqtus.types.units.Unit`."""

    @converter.register_unstructure_hook
    def unstructure_unit(unit: Unit) -> str:
        return str(unit)

    @converter.register_structure_hook
    def structure_unit(data, _) -> Unit:
        if not isinstance(data, str):
            raise ValueError(f"Expected a string for Unit, got {type(data)}: {data}")
        return Unit(data)
