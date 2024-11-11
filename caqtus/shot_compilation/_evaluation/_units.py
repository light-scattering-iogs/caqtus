from collections.abc import Mapping

from caqtus.types.units import Unit, unit_registry, UNITS

units: Mapping[str, Unit] = {unit: getattr(unit_registry, unit) for unit in UNITS}
