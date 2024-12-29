import itertools
from collections.abc import Mapping
from typing import assert_never

import attrs

from caqtus.types.parameter import Parameter
from caqtus.types.units import Unit, Quantity, dimensionless
from caqtus.types.variable_name import DottedVariableName

type ConstantSchema = Mapping[DottedVariableName, Parameter]
type VariableSchema = Mapping[DottedVariableName, ParameterType]
type ParameterType = (Boolean | Integer | Float | QuantityType)


class ParameterSchema(Mapping[DottedVariableName | str, ParameterType]):
    """Contains the type of each parameter in a sequence.

    More explicitly, it contains the value of the parameters that are constant during
    the sequence and the types of the parameters that can change during the sequence.
    The constant and variable parameters have no overlap.

    This object behaves like an immutable dictionary with the keys being the parameter
    names and the values being the types of the parameters.
    """

    def __init__(
        self,
        *,
        _constant_schema: ConstantSchema,
        _variable_schema: VariableSchema,
    ) -> None:
        if set(_constant_schema) & set(_variable_schema):
            raise ValueError(
                "The constant and variable schemas must not have any parameters in "
                "common."
            )
        self._constant_schema = _constant_schema
        self._variable_schema = _variable_schema

    def __len__(self):
        return len(self._constant_schema) + len(self._variable_schema)

    def __iter__(self):
        return itertools.chain(self._constant_schema, self._variable_schema)

    def __contains__(self, item) -> bool:
        return item in self._constant_schema or item in self._variable_schema

    def __getitem__(self, key: DottedVariableName | str) -> ParameterType:
        if isinstance(key, str):
            key = DottedVariableName(key)
        if key in self._constant_schema:
            return self.type_from_value(self._constant_schema[key])
        elif key in self._variable_schema:
            return self._variable_schema[key]
        else:
            raise KeyError(key)

    @property
    def constant_schema(self) -> ConstantSchema:
        """Values of the parameters that are constant during the sequence."""

        return self._constant_schema

    @property
    def variable_schema(self) -> VariableSchema:
        """Types of the parameters that can change during the sequence."""

        return self._variable_schema

    def __repr__(self) -> str:
        return (
            f"ParameterSchema("
            f"_constant_schema={self._constant_schema}, "
            f"_variable_schema={self._variable_schema})"
        )

    def __str__(self) -> str:
        constants = (
            f'"{key}": {value}' for key, value in self._constant_schema.items()
        )
        variables = (
            f'"{key}": {value}' for key, value in self._variable_schema.items()
        )
        joined = itertools.chain(constants, variables)
        return "{" + ", ".join(joined) + "}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ParameterSchema):
            return NotImplemented
        return (
            self._constant_schema == other._constant_schema
            and self._variable_schema == other._variable_schema
        )

    @classmethod
    def type_from_value(cls, value: Parameter) -> ParameterType:
        if isinstance(value, bool):
            return Boolean()
        elif isinstance(value, int):
            return Integer()
        elif isinstance(value, float):
            return Float()
        elif isinstance(value, Quantity):
            return QuantityType(units=value.units)
        else:
            assert_never(value)


@attrs.frozen
class QuantityType:
    units: Unit

    def convert(self, value: Parameter) -> Quantity[float]:
        """Convert a value to a quantity with the correct units.

        Raises:
            ValueError: If the value is not compatible with the units.
        """

        match value:
            case int() | float() | bool() as v:
                if self.units.is_compatible_with(dimensionless):
                    q = Quantity(v, dimensionless)
                    return q.to_unit(self.units)
                else:
                    raise ValueError(f"Can't coerce value {value} to quantity.")
            case Quantity() as q:
                if q.unit.is_compatible_with(self.units):
                    return q.to_unit(self.units)
                else:
                    raise ValueError(f"Can't coerce value {value} to quantity.")
            case _:
                assert_never(value)


@attrs.frozen
class Float:
    @property
    def units(self) -> None:
        return None

    @staticmethod
    def convert(value: Parameter) -> float:
        """Convert a value to a float.

        Raises:
            ValueError: If the value can't be converted to a float without loss of
                information.
        """

        match value:
            case bool(v):
                return float(v)
            case int(v):
                return float(v)
            case float(v):
                return v
            case Quantity() as q:
                if q.unit.is_compatible_with(dimensionless):
                    return q.to(dimensionless).magnitude
                else:
                    raise ValueError(f"Can't coerce quantity {value} to float.")
            case _:
                assert_never(value)


@attrs.frozen
class Boolean:
    @property
    def units(self) -> None:
        return None

    @staticmethod
    def convert(value: Parameter) -> bool:
        match value:
            case bool(v):
                return v
            case int(v):
                if v == 0:
                    return False
                elif v == 1:
                    return True
                else:
                    raise ValueError(f"Can't coerce integer {value} to boolean.")
            case float():
                raise ValueError(f"Can't coerce float {value} to boolean.")
            case Quantity():
                raise ValueError(f"Can't coerce quantity {value} to boolean.")
            case _:
                assert_never(value)


@attrs.frozen
class Integer:
    @property
    def units(self) -> None:
        return None

    @staticmethod
    def convert(value: Parameter) -> int:
        match value:
            case bool(v):
                return int(v)
            case int(v):
                return v
            case float():
                raise ValueError(f"Can't coerce float {value} to integer.")
            case Quantity():
                raise ValueError(f"Can't coerce quantity {value} to integer.")
            case _:
                assert_never(value)
