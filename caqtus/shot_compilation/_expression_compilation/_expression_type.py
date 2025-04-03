import attrs

from caqtus.types.units import BaseUnit


class Integer:
    pass


class Float:
    pass


@attrs.frozen
class Quantity:
    units: BaseUnit


class Boolean:
    pass


type ExpressionType = Integer | Float | Quantity | Boolean
