"""Defines how a parameter can be iterated over in a sequence."""

import math
from collections.abc import Mapping, Sequence
from typing import assert_never

import attrs

from caqtus.types.parameter import ParameterType, Parameter
from caqtus.types.units import Unit, Quantity, dimensionless
from caqtus.types.variable_name import DottedVariableName
from . import LinspaceLoop, ArangeLoop
from ._steps import Step, ExecuteShot, VariableDeclaration, ContainsSubSteps
from ._user_input_steps import DigitalUserInputStep, AnalogUserInputStep
from ..expression import Expression
from ..parameter._schema import Boolean, Integer, Float, QuantityType, ParameterSchema

type ParameterDefinition = (
    Constant
    | IteratedParameter
    | DigitalUserTunableParameter
    | AnalogUserTunableParameter
)


@attrs.frozen
class Constant:
    """A constant value that can be used in parameter definitions."""

    value: Parameter

    def parameter_type(self) -> ParameterType:
        """Returns the type of the constant value."""
        return ParameterSchema.type_from_value(self.value)

    def place(self) -> str:
        return "globals"

    def update(
        self, name: DottedVariableName, new_definition: ParameterDefinition
    ) -> ParameterDefinition:
        if not is_compatible(new_definition.parameter_type(), self.parameter_type()):
            raise TypeError(
                f"Cannot redefine global '{name}' with type "
                f"{self.parameter_type()} to {new_definition.parameter_type} in "
                f"{new_definition.place()}"
            )
        return new_definition

    def format(self, name: DottedVariableName) -> str:
        return f"{name}: {self.parameter_type()}"


@attrs.frozen
class IteratedParameter:
    """A parameter that is iterated over in a sequence."""

    step_definition: int
    type_: ParameterType

    def parameter_type(self) -> ParameterType:
        """Returns the type of the iterated parameter."""
        return self.type_

    def place(self) -> str:
        return f"step {self.step_definition}"

    def update(
        self, name: DottedVariableName, new_definition: ParameterDefinition
    ) -> ParameterDefinition:
        if not is_compatible(new_definition.parameter_type(), self.parameter_type()):
            raise TypeError(
                f"Conflicting definitions: `{self.format(name)}` and "
                f"`{new_definition.format(name)}`"
            )
        if isinstance(
            new_definition, DigitalUserTunableParameter | AnalogUserTunableParameter
        ):
            raise TypeError(
                f"Cannot redefine {self.format(name)} to {new_definition.format(name)}"
            )
        return new_definition

    def format(self, name: DottedVariableName) -> str:
        return f"(step {self.step_definition}) {name}: {self.type_}"


@attrs.frozen
class DigitalUserTunableParameter:
    step_definition: int

    def parameter_type(self) -> ParameterType:
        return Boolean()

    def place(self) -> str:
        return f"step {self.step_definition}"

    def update(
        self, name: DottedVariableName, new_definition: ParameterDefinition
    ) -> ParameterDefinition:
        if not isinstance(new_definition, DigitalUserTunableParameter):
            raise TypeError(
                f"Cannot redefine digital user tunable parameter {name} in "
                f"{new_definition.place()}"
            )
        return self

    def format(self, name: DottedVariableName) -> str:
        return f"(step {self.step_definition}) {name}: UserTunable<{self.parameter_type()}>"


@attrs.frozen
class AnalogUserTunableParameter:
    """A parameter that can be tuned by the user during sequence execution."""

    step_definition: int
    unit: Unit

    def parameter_type(self) -> ParameterType:
        return QuantityType(units=self.unit)

    def place(self) -> str:
        return f"step {self.step_definition}"

    def update(
        self, name: DottedVariableName, new_definition: ParameterDefinition
    ) -> ParameterDefinition:
        if not isinstance(new_definition, AnalogUserTunableParameter):
            raise TypeError(
                f"Cannot redefine analog user tunable parameter {name} in "
                f"{new_definition.place()}"
            )
        if not new_definition.unit.is_compatible_with(self.unit):
            raise TypeError(
                f"Cannot redefine analog user tunable parameter {name} with "
                f"incompatible units {self.unit} and {new_definition.unit}"
            )
        return self

    def format(self, name: DottedVariableName) -> str:
        return f"(step {self.step_definition}) {name}: UserTunable<{self.parameter_type()}>"


def compute_iteration_schema(
    steps: Sequence[Step],
    constants: Mapping[DottedVariableName, Parameter],
) -> dict[DottedVariableName, ParameterDefinition]:
    initial_symtable = SymTable(
        {name: Constant(value=parameter) for name, parameter in constants.items()}
    )
    step_index = 1
    for step in steps:
        step_index = _update_symtable(step_index, step, initial_symtable)
    return initial_symtable


class SymTable(dict[DottedVariableName, ParameterDefinition]):
    def parameter_schema(self) -> Mapping[DottedVariableName, ParameterType]:
        return {name: decl.parameter_type() for name, decl in self.items()}


def _update_symtable(
    step_index: int,
    step: Step,
    symtable: SymTable,
) -> int:
    match compute_definition(step, step_index, symtable):
        case None:
            pass
        case (variable, new_definition):
            if variable in symtable:
                previous_def = symtable[variable]
                symtable[variable] = previous_def.update(variable, new_definition)
            else:
                symtable[variable] = new_definition
    step_index += 1
    if isinstance(step, ContainsSubSteps):
        for sub_step in step.sub_steps:
            step_index = _update_symtable(step_index, sub_step, symtable)
    return step_index


def compute_definition(
    step: Step, step_index: int, symtable: SymTable
) -> tuple[DottedVariableName, ParameterDefinition] | None:
    match step:
        case ExecuteShot():
            return None
        case VariableDeclaration(variable=variable, value=value):
            type_ = get_expression_type(value, symtable.parameter_schema())
            return variable, IteratedParameter(step_definition=step_index, type_=type_)
        case LinspaceLoop(variable=variable, start=start, stop=stop) | ArangeLoop(
            variable=variable, start=start, stop=stop
        ):
            start_type = get_expression_type(start, symtable.parameter_schema())
            stop_type = get_expression_type(stop, symtable.parameter_schema())
            if not is_compatible(start_type, stop_type):
                raise TypeError(
                    f"Start and stop of loop {step_index} must be compatible, got "
                    f"{start_type} and {stop_type}."
                )
            if not isinstance(start_type, Float | QuantityType):
                raise TypeError(
                    f"Start and stop of loop {step_index} must be a float or quantity, not "
                    f"{start_type}."
                )
            return variable, IteratedParameter(
                step_definition=step_index, type_=start_type
            )
        case DigitalUserInputStep(variable):
            return variable, DigitalUserTunableParameter(step_index)
        case AnalogUserInputStep(variable, (a, b)):
            a_type = get_expression_type(a, symtable.parameter_schema())
            b_type = get_expression_type(b, symtable.parameter_schema())
            if not is_compatible(a_type, b_type):
                raise TypeError(
                    f"Range of analog user input step {step_index} must be compatible, "
                    f"got {a_type} and {b_type}."
                )
            if not isinstance(a_type, QuantityType):
                raise TypeError(
                    f"Range of analog user input step {step_index} must be a quantity, "
                    f"not {a_type}."
                )
            return variable, AnalogUserTunableParameter(
                step_definition=step_index,
                unit=a_type.units,
            )

        case _:
            assert_never(step)


def get_expression_type(
    expr: Expression, schema: Mapping[DottedVariableName, ParameterType]
) -> ParameterType:
    dependant_variables = expr.upstream_variables

    undefined_variables = dependant_variables - schema.keys()

    if undefined_variables:
        raise ValueError(
            f"Expression {expr} depends on undefined variables: {undefined_variables}"
        )
    values = {var: _example_value(schema[var]) for var in dependant_variables}
    result = expr.evaluate(values)
    type_ = ParameterSchema.type_from_value(result)
    return type_


def _example_value(type_: ParameterType) -> Parameter:
    match type_:
        case Boolean():
            return True
        case Integer():
            return 1
        case Float():
            return math.nan
        case QuantityType(units):
            return Quantity(magnitude=math.nan, units=units)
        case _:
            assert_never(type_)


def is_compatible(type1: ParameterType, type2: ParameterType) -> bool:
    match type1:
        case Boolean():
            match type2:
                case Boolean():
                    return True
                case _:
                    return False
        case Integer():
            match type2:
                case Integer():
                    return True
                case _:
                    return False
        case Float():
            match type2:
                case Float():
                    return True
                case QuantityType(units):
                    if units.is_compatible_with(dimensionless):
                        return True
                    return False
                case _:
                    return False
        case QuantityType(units1):
            match type2:
                case Float():
                    return units1.is_compatible_with(dimensionless)
                case QuantityType(units2):
                    return units1.is_compatible_with(units2)
                case _:
                    return False
