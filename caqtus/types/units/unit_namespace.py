from collections.abc import Mapping

from ._units import UNITS, ureg, Unit

units: Mapping[str, Unit] = {unit: getattr(ureg, unit) for unit in UNITS}
