import functools
from collections.abc import Iterable, Mapping, Callable
from typing import assert_never, Any

import numpy

from core.compilation import units
from core.session import ConstantTable
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
)
from core.types.parameter.analog_value import add_unit
from core.types.variable_name import DottedVariableName
from .sequence_manager import SequenceManager
from .step_context import StepContext


def wrap_error(function: Callable[[Any, Step, StepContext], StepContext]):
    @functools.wraps(function)
    def wrapper(self, step: Step, context: StepContext):
        try:
            return function(self, step, context)
        except Exception as e:
            raise StepEvaluationError(f"Error while evaluating step <{step}>") from e

    return wrapper


class StepSequenceRunner:
    def __init__(
        self,
        sequence_manager: SequenceManager,
        constant_tables: Mapping[str, ConstantTable],
    ):
        self._sequence_manager = sequence_manager
        self._constant_tables = constant_tables

    def execute_steps(self, steps: Iterable[Step]):
        context = StepContext()

        for step in steps:
            context = self.run_step(step, context)

    @functools.singledispatchmethod
    @wrap_error
    def run_step(self, step: Step, context: StepContext) -> StepContext:
        """Execute a given step of the sequence

        This function should be implemented for each Step type.

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

        This function evaluates the expression of the declaration and updates the value
        of the variable in the context.
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
        """Loop over a variable in a numpy arange like loop."""

        start, stop, step = evaluate_arange_loop_parameters(arange_loop, context)

        unit = get_unit(start)
        start_magnitude = magnitude_in_unit(start, unit)
        stop_magnitude = magnitude_in_unit(stop, unit)
        step_magnitude = magnitude_in_unit(step, unit)

        variable_name = arange_loop.variable
        for value in numpy.arange(start_magnitude, stop_magnitude, step_magnitude):
            value_with_unit = add_unit(value, unit)
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
        """Loop over a variable in a numpy linspace like loop"""

        start, stop, num = evaluate_linspace_loop_parameters(linspace_loop, context)

        unit = get_unit(start)
        start_magnitude = magnitude_in_unit(start, unit)
        stop_magnitude = magnitude_in_unit(stop, unit)

        variable_name = linspace_loop.variable
        for value in numpy.linspace(start_magnitude, stop_magnitude, num):
            value_with_unit = add_unit(value, unit)
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
            raise ValueError(
                f"Constant table <{table_name}> does not exist. Available tables are "
                f"<{', '.join(self._constant_tables)}>"
            )
        table = self._constant_tables[table_name]
        namespace = import_constant_table.alias or table_name
        table_context = StepContext()
        for declaration in table:
            try:
                table_context = self.run_step(declaration, table_context)
            except Exception as e:
                print(e)
                raise
        for name, value in table_context.variables.to_flat_dict().items():
            context = context.update_variable(
                DottedVariableName(f"{namespace}.{name}"), value
            )
        return context

    @run_step.register
    @wrap_error
    def _(self, shot: ExecuteShot, context: StepContext) -> StepContext:
        print(context.variables)

        return context

        # self._sequence_manager.schedule_shot(shot.name, context)
        # return context.reset_history()


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
