import itertools
from collections.abc import Mapping
from typing import assert_never

import attrs
import polars

from caqtus.types.parameter import Parameter
from caqtus.types.units import Unit, Quantity
from caqtus.types.variable_name import DottedVariableName

type ConstantSchema = Mapping[DottedVariableName, Parameter]
type VariableSchema = Mapping[DottedVariableName, ParameterType]
type ParameterType = Boolean | Integer | Float | QuantityType


class ParameterSchema(Mapping[DottedVariableName | str, ParameterType]):
    """Contains the type of each parameter in a sequence."""

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

    @staticmethod
    def to_polars_dtype() -> polars.DataType:
        return polars.Float64()

    def to_polars_value(self, value) -> float:
        if not isinstance(value, Quantity):
            raise ValueError(f"Expected a Quantity, got {value!r}.")
        magnitude = value.to_unit(self.units).magnitude
        if not isinstance(magnitude, float):
            raise ValueError(f"Expected a float, got {magnitude!r}.")
        return magnitude

    def __str__(self):
        return f"Quantity<{self.units.dimensionality}>"


@attrs.frozen
class Float:
    @property
    def units(self) -> None:
        return None

    @staticmethod
    def to_polars_dtype() -> polars.DataType:
        return polars.Float64()

    @staticmethod
    def to_polars_value(value) -> float:
        if not isinstance(value, float):
            raise ValueError(f"Expected a float, got {value!r}.")
        return value


@attrs.frozen
class Boolean:
    @property
    def units(self) -> None:
        return None

    @staticmethod
    def to_polars_dtype() -> polars.DataType:
        return polars.Boolean()

    @staticmethod
    def to_polars_value(value) -> bool:
        if not isinstance(value, bool):
            raise ValueError(f"Expected a bool, got {value!r}.")
        return value

    def __str__(self):
        return "boolean"


@attrs.frozen
class Integer:
    @property
    def units(self) -> None:
        return None

    @staticmethod
    def to_polars_dtype() -> polars.DataType:
        return polars.Int64()

    @staticmethod
    def to_polars_value(value) -> int:
        if not isinstance(value, int):
            raise ValueError(f"Expected an int, got {value!r}.")
        return value

    def __str__(self):
        return "integer"
