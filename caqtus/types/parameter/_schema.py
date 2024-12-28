from collections.abc import Mapping
from typing import assert_never

import attrs

from caqtus.types.parameter import Parameter
from caqtus.types.units import Unit, Quantity
from caqtus.types.variable_name import DottedVariableName

type ConstantSchema = Mapping[DottedVariableName, Parameter]
type VariableSchema = Mapping[DottedVariableName, ParameterType]
type ParameterType = (
    ParameterSchema.Boolean
    | ParameterSchema.Integer
    | ParameterSchema.Float
    | ParameterSchema.Quantity
)


class ParameterSchema:
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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ParameterSchema):
            return NotImplemented
        return (
            self._constant_schema == other._constant_schema
            and self._variable_schema == other._variable_schema
        )

    @attrs.frozen
    class Quantity:
        unit: Unit

    @attrs.frozen
    class Float:
        pass

    @attrs.frozen
    class Boolean:
        pass

    @attrs.frozen
    class Integer:
        pass

    @classmethod
    def type_from_value(cls, value: Parameter) -> ParameterType:
        if isinstance(value, bool):
            return cls.Boolean()
        elif isinstance(value, int):
            return cls.Integer()
        elif isinstance(value, float):
            return cls.Float()
        elif isinstance(value, Quantity):
            return cls.Quantity(unit=value.units)
        else:
            assert_never(value)
