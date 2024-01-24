from collections.abc import Mapping

from core.types.units import UNITS, ureg, Unit
from core.types.variable_name import VariableName

units: Mapping[VariableName, Unit] = {
    VariableName(unit): getattr(ureg, unit) for unit in UNITS
}
