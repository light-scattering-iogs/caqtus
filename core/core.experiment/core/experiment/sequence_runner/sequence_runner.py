import functools
from collections.abc import Iterable, Callable
from typing import assert_never, Any

import numpy

from core.compilation import units
from core.session import ParameterNamespace
from core.session.sequence.iteration_configuration import (
    Step,
    ArangeLoop,
    ExecuteShot,
    VariableDeclaration,
    LinspaceLoop,
    ImportConstantTable,
)
from core.types.parameter import (
    is_analog_value,
    AnalogValue,
    get_unit,
    magnitude_in_unit,
    is_parameter,
    Parameter,
)
from core.types.parameter.analog_value import add_unit
from core.types.variable_name import DottedVariableName
from .sequence_manager import SequenceManager, SequenceInterruptedException
from .step_context import StepContext


def wrap_error(function: Callable[[Any, Step, StepContext], StepContext]):
    """Wrap a function that evaluates a step to raise nicer errors for the user."""

    @functools.wraps(function)
    def wrapper(self, step: Step, context: StepContext):
        try:
            return function(self, step, context)
        except SequenceInterruptedException:
            # Don't want to add user context to this exception
            raise
        except Exception as e:
            raise StepEvaluationError(f"Error while evaluating step <{step}>") from e

    return wrapper


class StepSequenceRunner:
    """Execute a sequence of steps on the experiment."""

    def __init__(
        self,
        sequence_manager: SequenceManager,
        initial_parameters: ParameterNamespace,
    ):
        self._sequence_manager = sequence_manager
        self._initial_parameters = initial_parameters

    def execute_steps(self, steps: Iterable[Step]):
        """Execute a sequence of steps on the experiment.

        This method will recursively execute each step in the sequence passed as
        argument.
        Before executing the sequence, an empty context is initialized.
        The context holds the value of the parameters at a given point in the sequence.
        Each step has the possibility to update the context with new values.
        """

        context = StepContext[Parameter]()

        for step in steps:
            context = self.run_step(step, context)

    @functools.singledispatchmethod
    @wrap_error
    def run_step(self, step: Step, context: StepContext) -> StepContext:
        """Execute a given step of the sequence

        This function is implemented for each Step type.

        Args:
            step: the step of the sequence currently executed
            context: Contains the values of the variables before this step.

        Returns:
            A new context object that contains the values of the variables after this
            step.
            This context object must be a new object.
        """

        return assert_never(step)

    @run_step.register
    @wrap_error
    def _(
        self,
        declaration: VariableDeclaration,
        context: StepContext,
    ) -> StepContext:
        """Execute a VariableDeclaration step.

        This step updates the context passed with the value of the variable declared.
        """

        value = declaration.value.evaluate(context.variables | units)
        if not is_parameter(value):
            raise TypeError(
                f"Value of variable declaration <{declaration}> has type "
                f"{type(value)}, which is not a valid parameter type."
            )
        return context.update_variable(declaration.variable, value)

    @run_step.register
    @wrap_error
    def _(
        self,
        arange_loop: ArangeLoop,
        context: StepContext,
    ):
        """Loop over a variable in a numpy arange like loop.

        This function will loop over the variable defined in the arange loop and execute
        the sub steps for each value of the variable.

        Returns:
            A new context object containing the value of the arange loop variable after
            the last iteration, plus the values of the variables defined in the sub
            steps.
        """

        start, stop, step = evaluate_arange_loop_parameters(arange_loop, context)

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
                context = self.run_step(step, context)
        return context

    @run_step.register
    @wrap_error
    def _(
        self,
        linspace_loop: LinspaceLoop,
        context: StepContext,
    ):
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
                context = self.run_step(step, context)
        return context

    @run_step.register
    @wrap_error
    def _(
        self, import_constant_table: ImportConstantTable, context: StepContext
    ) -> StepContext:
        """Import a constant table into the context."""

        table_name = import_constant_table.table
        if table_name not in self._constant_tables:
            exception = ValueError(f"Constant table <{table_name}> is not available.")
            exception.add_note(
                f"Available tables are <{', '.join(self._constant_tables)}>"
            )
            raise exception
        table = self._constant_tables[table_name]
        namespace = import_constant_table.alias or table_name
        table_context = StepContext()
        for declaration in table:
            table_context = self.run_step(declaration, table_context)
        for name, value in table_context.variables.to_flat_dict().items():
            context = context.update_variable(
                DottedVariableName(f"{namespace}.{name}"), value
            )
        return context

    @run_step.register
    @wrap_error
    def _(self, shot: ExecuteShot, context: StepContext) -> StepContext:
        """Schedule a shot to be run.

        This function schedule to run a shot on the experiment with the parameters
        defined in the context at this point.

        Returns:
            The context passed as argument unchanged.
        """

        self._sequence_manager.schedule_shot(context.variables)
        return context


def evaluate_arange_loop_parameters(
    arange_loop: ArangeLoop,
    context: StepContext,
) -> tuple[AnalogValue, AnalogValue, AnalogValue]:
    variables = context.variables | units

    start = arange_loop.start.evaluate(variables)
    if not is_analog_value(start):
        raise TypeError(f"Start of loop '{arange_loop}' is not an analog value.")
    stop = arange_loop.stop.evaluate(variables)
    if not is_analog_value(stop):
        raise TypeError(f"Stop of loop '{arange_loop}' is not an analog value.")
    step = arange_loop.step.evaluate(variables)
    if not is_analog_value(step):
        raise TypeError(f"Step of loop '{arange_loop}' is not an analog value.")
    return start, stop, step


def evaluate_linspace_loop_parameters(
    linspace_loop: LinspaceLoop,
    context: StepContext,
) -> tuple[AnalogValue, AnalogValue, int]:
    variables = context.variables | units

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
