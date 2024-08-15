from collections.abc import Mapping

from ._units import UNITS, ureg, Unit
from ..variable_name import VariableName

units: Mapping[VariableName, Unit] = {
    VariableName(unit): getattr(ureg, unit) for unit in UNITS
}
