from collections.abc import Mapping

from caqtus.types.units import UNITS, ureg, Unit
from caqtus.types.variable_name import VariableName

units: Mapping[VariableName, Unit] = {
    VariableName(unit): getattr(ureg, unit) for unit in UNITS
}
