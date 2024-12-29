from collections.abc import Mapping
from typing import assert_never, Optional, Self

import attrs

from caqtus.types.parameter import Parameter
from caqtus.types.units import Unit, Quantity, dimensionless
from caqtus.types.variable_name import DottedVariableName

type ConstantSchema = Mapping[DottedVariableName, Parameter]
type VariableSchema = Mapping[DottedVariableName, ParameterType]
type ParameterType = (Boolean | Integer | Float | QuantityType | Constant)


@attrs.frozen
class ParameterSchema(Mapping[DottedVariableName | str, ParameterType]):
    """Contains the type of each parameter in a sequence.

    This object behaves like an immutable dictionary with the keys being the parameter
    names and the values being the types of the parameters.
    """

    parameter_types: Mapping[DottedVariableName, ParameterType]

    @classmethod
    def create(cls, *, constants: ConstantSchema, variables: VariableSchema) -> Self:
        """Create a schema from a set of constant and variable parameters.

        Raises:
            ValueError: If some constants and variables have the same name.
        """

        intersection = set(constants) & set(variables)
        if intersection:
            raise ValueError(
                "These names are defined both as constants and variables: "
                f"{intersection}"
            )
        constant_types = {name: Constant(value) for name, value in constants.items()}
        return cls({**constant_types, **variables})

    def __len__(self):
        return len(self.parameter_types)

    def __iter__(self):
        return iter(self.parameter_types)

    def __contains__(self, item) -> bool:
        return item in self.parameter_types

    def __getitem__(self, key: DottedVariableName | str) -> ParameterType:
        if isinstance(key, str):
            key = DottedVariableName(key)
        return self.parameter_types[key]

    def __str__(self) -> str:
        formatted = (f'"{key}": {value}' for key, value in self.parameter_types.items())
        return "{" + ", ".join(formatted) + "}"

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

    def enforce(
        self, values: Mapping[DottedVariableName, Parameter]
    ) -> Mapping[DottedVariableName, Parameter]:
        """Enforce the schema on a set of values.

        This method checks that the values are compatible with the schema and returns a
        dictionary with the same keys and the values coerced to the expected types
        defined in the schema.

        Raises:
            KeyError: If a parameter is missing from the values passed to the method.
            InvalidConstantValueError: If a value defined to be constant in the
                schema is not equal to the expected value.
            CoercionError: If a value can't be coerced to the expected type.
            ExtraParametersError: If more parameters are present in the values than
                in the schema.
        """

        values = dict(values)

        result = {}
        for variable_name, variable_type in self.parameter_types.items():
            value = values.pop(variable_name)
            try:
                converted = variable_type.convert(value)
            except ValueError as e:
                raise CoercionError(
                    f"Parameter {variable_name} cannot be converted to the expected "
                    f"type: {variable_type}"
                ) from e
            result[variable_name] = converted

        if values:
            raise ValueError(f"Unexpected parameters: {values.keys()}")

        return result


class InvalidConstantValueError(ValueError):
    """Raised when a constant value is not compatible with the schema."""


class ExtraParametersError(ValueError):
    """Raised when extra parameters are passed to a function."""


class CoercionError(ValueError):
    """Raised when a value can't be coerced to the expected type."""


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

    def __str__(self):
        return f"Quantity(_, {self.units:~}"


@attrs.frozen
class Constant:
    value: Parameter

    @property
    def units(self) -> Optional[Unit]:
        if isinstance(self.value, Quantity):
            return self.value.units
        else:
            return None

    def convert(self, value: Parameter) -> Parameter:
        if value != self.value:
            raise ValueError(f"Value {value} must be {self.value}.")
        return self.value

    def __str__(self):
        if isinstance(self.value, Quantity):
            return f"Constant({self.value:~})"
        else:
            return f"Constant({self.value})"


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

    def __str__(self):
        return "float()"


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

    def __str__(self):
        return "bool()"


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

    def __str__(self):
        return "int()"
