from collections.abc import Mapping

from ._units import UNITS, Unit, ureg

# TODO: Some tests fail when trying to replace `getattr(ureg, unit)` with `Unit(unit)`.
#  To check.
units: Mapping[str, Unit] = {unit: getattr(ureg, unit) for unit in UNITS}
