from collections.abc import Mapping

from caqtus.types.units import Quantity, Unit
from ._scalar import Scalar

CONSTANTS: Mapping[str, Scalar] = {
    "pi": Quantity(3.141592653589793, Unit("rad")),
    "e": 2.718281828459045,
    "Enabled": True,
    "Disabled": False,
}
