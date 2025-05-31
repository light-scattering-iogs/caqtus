from __future__ import annotations

import functools
from collections.abc import Callable, Generator, Iterable, Iterator, Mapping
from typing import Self, assert_never, override

import attrs

import caqtus.formatter as fmt
from caqtus.types.parameter import (
    NotAnalogValueError,
    Parameter,
    ParameterSchema,
    is_parameter,
)
from caqtus.types.recoverable_exceptions import InvalidTypeError
from caqtus.utils import serialization

from ..recoverable_exceptions import EvaluationError
from ..units import InvalidDimensionalityError
from ..variable_name import DottedVariableName
from ._converter import _converter
from ._step_context import StepContext
from ._steps import (
    ArangeLoop,
    ExecuteShot,
    LinspaceLoop,
    Step,
    VariableDeclaration,
    validate_step,
)
from ._tunable_parameter_config import (
    InputType,
    TunableParameterConfig,
    evaluate_tunable_parameter_config,
    tunable_parameter_type,
)
from .iteration_configuration import IterationConfiguration, Unknown


@attrs.define
class StepsConfiguration(IterationConfiguration):
    """Define the parameter iteration of a sequence as a list of steps.

    Attributes:
        steps: The steps of the iteration.
        tunable_parameters: A list of configurations for the parameters that are tunable
            by the user during the execution of the sequence.

            Each element of the list is a tuple containing the name of the parameter
            and its configuration.
            If two parameter configurations have the same name, or if they overlap with
            the parameters defined in the steps, an error will be raised when the
            sequence is executed.
    """

    steps: list[Step] = attrs.field(
        validator=attrs.validators.deep_iterable(
            iterable_validator=attrs.validators.instance_of(list),
            member_validator=validate_step,
        ),
        on_setattr=attrs.setters.validate,
    )
    tunable_parameters: list[tuple[DottedVariableName, TunableParameterConfig]] = (
        attrs.field(factory=list)
    )

    @classmethod
    def empty(cls) -> Self:
        return cls(steps=[])

    def expected_number_shots(self) -> int | Unknown:
        """Returns the expected number of shots that will be executed by the sequence.

        Returns:
            A positive integer if the number of shots can be determined, or Unknown if
            the number of shots cannot be determined.
        """

        return sum(expected_number_shots(step) for step in self.steps)

    def get_parameter_names(self) -> set[DottedVariableName]:
        return self.get_step_parameter_names() | self.get_tunable_parameter_names()

    def get_step_parameter_names(self) -> set[DottedVariableName]:
        """Return the names of the parameters that are defined in the steps."""
        return set().union(*[get_parameter_names(step) for step in self.steps])

    def get_tunable_parameter_names(self) -> set[DottedVariableName]:
        """Return the names of the tunable parameters."""
        return {name for name, _ in self.tunable_parameters}

    @classmethod
    def dump(cls, steps_configuration: StepsConfiguration) -> serialization.JSON:
        return _converter.unstructure(steps_configuration, StepsConfiguration)

    @classmethod
    def load(cls, data: serialization.JSON) -> StepsConfiguration:
        return _converter.structure(data, StepsConfiguration)

    def walk(self, initial_context: StepContext) -> Iterator[StepContext]:
        """Returns the context for every shot encountered while walking the steps."""

        return walk_steps(self.steps, initial_context)

    @override
    def get_parameter_schema(
        self, initial_parameters: Mapping[DottedVariableName, Parameter]
    ) -> ParameterSchema:
        tunable_parameters = evaluate_tunable_parameter_configs(
            self.tunable_parameters, initial_parameters
        )
        tunable_parameter_schema = {
            name: tunable_parameter_type(config)
            for name, config in tunable_parameters.items()
        }

        context_iterator = self.walk(StepContext(initial_parameters))
        try:
            first_context = next(context_iterator)
        except StopIteration:
            # In case there are no steps to walk, we return a schema made only of the
            # tunable parameters.
            return ParameterSchema(
                _constant_schema=initial_parameters,
                _variable_schema=tunable_parameter_schema,
            )
        tunable_parameters = self.get_tunable_parameter_names()
        step_parameters = self.get_step_parameter_names()

        if intersection := step_parameters & tunable_parameters:
            raise IntersectionParametersError.from_intersection(intersection)

        constant_parameters = (
            set(initial_parameters) - tunable_parameters - step_parameters
        )
        constant_schema = {
            name: initial_parameters[name] for name in constant_parameters
        }
        initial_step_values = first_context.variables.to_flat_dict()
        step_schema = {
            name: ParameterSchema.type_from_value(initial_step_values[name])
            for name in step_parameters
        }
        variable_schema = step_schema | tunable_parameter_schema
        assert set(variable_schema) & set(constant_schema) == set()

        return ParameterSchema(
            _constant_schema=constant_schema, _variable_schema=variable_schema
        )


class IntersectionParametersError(ValueError):
    @classmethod
    def from_intersection(cls, intersection: set[DottedVariableName]) -> Self:
        """Create an error from the intersection of tunable and step parameters."""
        err = cls(
            f"Parameters {intersection} are both defined as tunable "
            "parameters and are being iterated over, which is not allowed."
        )
        err.add_note(
            "To fix this, remove the duplicate definition for these parameters."
        )
        return err


def evaluate_tunable_parameter_configs(
    tunable_parameters: list[tuple[DottedVariableName, TunableParameterConfig]],
    initial_parameters: Mapping[DottedVariableName, Parameter],
) -> Mapping[DottedVariableName, InputType]:
    evaluated_inputs = {}
    for name, config in tunable_parameters:
        if name in evaluated_inputs:
            error = ValueError(f"Tunable parameter '{name}' is defined multiple times.")
            error.add_note("To fix this, remove the duplicate definition.")
            raise error
        evaluated_inputs[name] = evaluate_tunable_parameter_config(
            config, initial_parameters
        )
    return evaluated_inputs


def expected_number_shots(
    step: Step,
) -> int | Unknown:
    match step:
        case VariableDeclaration():
            return 0
        case ExecuteShot():
            return 1
        case LinspaceLoop(num=num, sub_steps=sub_steps):
            sub_steps_number = sum(
                expected_number_shots(sub_step) for sub_step in sub_steps
            )
            return sub_steps_number * num
        case ArangeLoop(sub_steps=sub_steps):
            try:
                length = len(list(step.loop_values({})))
            except (EvaluationError, NotAnalogValueError, InvalidDimensionalityError):
                # The errors above can occur if the steps are still being edited or if
                # the expressions depend on other variables that are not defined here.
                # These can be errors on the user side, so we don't want to crash on
                # them, and we just indicate that we don't know the number of shots.
                return Unknown()
            sub_steps_number = sum(
                expected_number_shots(sub_step) for sub_step in sub_steps
            )
            return sub_steps_number * length
        case _:
            assert_never(step)


def get_parameter_names(step: Step) -> set[DottedVariableName]:
    match step:
        case VariableDeclaration(variable=variable, value=_):
            return {variable}
        case ExecuteShot():
            return set()
        case LinspaceLoop(variable=variable, sub_steps=sub_steps) | ArangeLoop(
            variable=variable, sub_steps=sub_steps
        ):
            return {variable}.union(
                *[get_parameter_names(sub_step) for sub_step in sub_steps]
            )
        case _:
            assert_never(step)


def wrap_error[
    S: Step
](
    function: Callable[[S, StepContext], Generator[StepContext, None, StepContext]],
) -> Callable[[S, StepContext], Generator[StepContext, None, StepContext]]:
    """Wrap a function that evaluates a step to raise nicer errors for the user."""

    @functools.wraps(function)
    def wrapper(step: S, context: StepContext):
        try:
            return function(step, context)
        except Exception as e:
            raise StepEvaluationError(f"Error while evaluating step <{step}>") from e

    return wrapper


def walk_steps(
    steps: Iterable[Step], initial_context: StepContext
) -> Iterator[StepContext]:
    """Yields the context for each shot defined by the steps.

    This function will recursively evaluate each step in the sequence passed as
    argument.
    Before executing the sequence, an empty context is initialized.
    The context holds the value of the parameters at a given point in the sequence.
    Each step has the possibility to update the context with new values.
    """

    context = initial_context

    for step in steps:
        context = yield from walk_step(step, context)


@functools.singledispatch
@wrap_error
def walk_step(
    step: Step, context: StepContext
) -> Generator[StepContext, None, StepContext]:
    """Iterates over the steps of a sequence.

    Args:
        step: the step of the sequence currently executed
        context: Contains the values of the variables before this step.

    Yields:
        The context for every shot encountered while walking the steps.

    Returns:
        The context after the step passed in argument has been executed.
    """

    raise NotImplementedError(f"Cannot walk step {step}")


# noinspection PyUnreachableCode
@walk_step.register
@wrap_error
def _(
    declaration: VariableDeclaration,
    context: StepContext,
) -> Generator[StepContext, None, StepContext]:
    """Execute a VariableDeclaration step.

    This step updates the context passed with the value of the variable declared.
    """

    value = declaration.value.evaluate(context.variables.dict())
    if not is_parameter(value):
        raise InvalidTypeError(
            f"{fmt.expression(declaration.value)}> does not evaluate to a parameter, "
            f"but to {fmt.type_(type(value))}.",
        )
    return context.update_variable(declaration.variable, value)

    # This code is unreachable, but it is kept here to make the function a generator.
    if False:
        yield context


@walk_step.register
@wrap_error
def _(
    arange_loop: ArangeLoop,
    context: StepContext,
) -> Generator[StepContext, None, StepContext]:
    """Loop over a variable in a numpy arange like loop.

    This function will loop over the variable defined in the arange loop and execute
    the sub steps for each value of the variable.

    Returns:
        A new context object containing the value of the arange loop variable after
        the last iteration, plus the values of the variables defined in the sub
        steps.
    """

    for value in arange_loop.loop_values(context.variables.dict()):
        context = context.update_variable(arange_loop.variable, value)
        for step in arange_loop.sub_steps:
            context = yield from walk_step(step, context)
    return context


@walk_step.register
@wrap_error
def _(
    linspace_loop: LinspaceLoop,
    context: StepContext,
) -> Generator[StepContext, None, StepContext]:
    """Loop over a variable in a numpy linspace like loop.

    This function will loop over the variable defined in the linspace loop and
    execute the sub steps for each value of the variable.

    Returns:
        A new context object containing the value of the linspace loop variable
        after the last iteration, plus the values of the variables defined in the
        sub steps.
    """

    for value in linspace_loop.loop_values(context.variables.dict()):
        context = context.update_variable(linspace_loop.variable, value)
        for step in linspace_loop.sub_steps:
            context = yield from walk_step(step, context)
    return context


@walk_step.register
@wrap_error
def _(
    shot: ExecuteShot, context: StepContext
) -> Generator[StepContext, None, StepContext]:
    """Schedule a shot to be run.

    This function schedules a shot on the experiment with the parameters
    defined in the context at this point.

    Returns:
        The context passed as argument unchanged.
    """

    yield context
    return context


class StepEvaluationError(Exception):
    pass
