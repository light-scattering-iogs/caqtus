from collections.abc import Mapping

from ._units import UNITS, Unit

units: Mapping[str, Unit] = {unit: Unit(unit) for unit in UNITS}
