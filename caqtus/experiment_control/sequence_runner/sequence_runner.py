import functools
from collections.abc import Iterable, Callable, Generator
from typing import assert_never, TypeVar

import numpy

from caqtus.session import ParameterNamespace
from caqtus.session.sequence.iteration_configuration import (
    Step,
    ArangeLoop,
    ExecuteShot,
    VariableDeclaration,
    LinspaceLoop,
)
from caqtus.types.parameter import (
    is_analog_value,
    AnalogValue,
    get_unit,
    magnitude_in_unit,
    is_parameter,
    Parameter,
)
from caqtus.types.parameter.analog_value import add_unit
from .sequence_manager import SequenceManager
from .step_context import StepContext
from ...session.sequence.iteration_configuration.steps_configurations import (
    evaluate_arange_loop_parameters,
)

S = TypeVar("S", bound=Step)


def wrap_error(
    function: Callable[[S, StepContext], Generator[StepContext, None, StepContext]]
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
) -> Iterable[StepContext]:
    """Yields the context for each shot defined by the steps.

    This function will recursively execute each step in the sequence passed as
    argument.
    Before executing the sequence, an empty context is initialized.
    The context holds the value of the parameters at a given point in the sequence.
    Each step has the possibility to update the context with new values.
    """

    context = initial_context

    for step in steps:
        context = yield from walk_step(step, context)


class StepSequenceRunner:
    """Execute a sequence of steps on the experiment."""

    def __init__(
        self,
        sequence_manager: SequenceManager,
        initial_parameters: ParameterNamespace,
    ):
        self._sequence_manager = sequence_manager
        self._initial_parameters = initial_parameters

    def execute_steps(
        self, steps: Iterable[Step], initial_context: StepContext[Parameter]
    ):
        """Execute a sequence of steps on the experiment.

        This method will recursively execute each step in the sequence passed as
        argument.
        Before executing the sequence, an empty context is initialized.
        The context holds the value of the parameters at a given point in the sequence.
        Each step has the possibility to update the context with new values.
        """

        for context in walk_steps(steps, initial_context):
            self._sequence_manager.schedule_shot(context.variables)


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

    return assert_never(step)  # type: ignore


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

    # This code is unreachable, but it is kept here to make the function a generator.
    if False:
        yield context

    value = declaration.value.evaluate(context.variables.dict())
    if not is_parameter(value):
        raise TypeError(
            f"Value of variable declaration <{declaration}> has type "
            f"{type(value)}, which is not a valid parameter type."
        )
    return context.update_variable(declaration.variable, value)


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

    start, stop, step = evaluate_arange_loop_parameters(
        arange_loop, context.variables.dict()
    )

    unit = get_unit(start)
    start_magnitude = magnitude_in_unit(start, unit)
    stop_magnitude = magnitude_in_unit(stop, unit)
    step_magnitude = magnitude_in_unit(step, unit)

    variable_name = arange_loop.variable
    for value in numpy.arange(start_magnitude, stop_magnitude, step_magnitude):
        # val.item() is used to convert numpy scalar to python scalar
        value_with_unit = add_unit(value.item(), unit)
        context = context.update_variable(variable_name, value_with_unit)
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

    start, stop, num = evaluate_linspace_loop_parameters(linspace_loop, context)

    unit = get_unit(start)
    start_magnitude = magnitude_in_unit(start, unit)
    stop_magnitude = magnitude_in_unit(stop, unit)

    variable_name = linspace_loop.variable
    for value in numpy.linspace(start_magnitude, stop_magnitude, num):
        # val.item() is used to convert numpy scalar to python scalar
        value_with_unit = add_unit(value.item(), unit)
        context = context.update_variable(variable_name, value_with_unit)
        for step in linspace_loop.sub_steps:
            context = yield from walk_step(step, context)
    return context


@walk_step.register
@wrap_error
def _(
    shot: ExecuteShot, context: StepContext
) -> Generator[StepContext, None, StepContext]:
    """Schedule a shot to be run.

    This function schedule to run a shot on the experiment with the parameters
    defined in the context at this point.

    Returns:
        The context passed as argument unchanged.
    """

    yield context
    return context


def evaluate_linspace_loop_parameters(
    linspace_loop: LinspaceLoop,
    context: StepContext,
) -> tuple[AnalogValue, AnalogValue, int]:
    variables = context.variables.dict()

    start = linspace_loop.start.evaluate(variables)
    if not is_analog_value(start):
        raise TypeError(f"Start of loop '{linspace_loop}' is not an analog value.")
    stop = linspace_loop.stop.evaluate(variables)
    if not is_analog_value(stop):
        raise TypeError(f"Stop of loop '{linspace_loop}' is not an analog value.")
    num = linspace_loop.num
    if num < 0:
        raise ValueError(f"Number of points of loop '{linspace_loop}' is negative.")
    return start, stop, num


class StepEvaluationError(Exception):
    pass


def evaluate_initial_context(parameters: ParameterNamespace) -> StepContext:
    """Evaluate the initial context of the sequence from the parameters."""

    flat_parameters = parameters.flatten()

    context = StepContext[Parameter]()

    for name, expression in flat_parameters:
        value = expression.evaluate({})
        if not is_parameter(value):
            raise TypeError(
                f"Expression <{expression}> for parameter <{name}> does not evaluate "
                f"to a valid parameter type, got <{type(value)}>."
            )
        context = context.update_variable(name, value)

    return context
