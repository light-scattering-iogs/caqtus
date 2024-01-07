import functools
from collections.abc import Iterable
from typing import assert_never

import numpy

from core.session.sequence.iteration_configuration import (
    Step,
    ArangeLoop,
    ExecuteShot,
    VariableDeclaration,
)
from core.types.parameter import (
    is_analog_value,
    AnalogValue,
    get_unit,
    magnitude_in_unit,
    is_parameter,
)
from core.types.parameter.analog_value import add_unit
from .sequence_manager import SequenceManager
from .step_context import StepContext
from ..unit_namespace import units


class StepSequenceRunner:
    def __init__(
        self,
        sequence_manager: SequenceManager,
    ):
        self._sequence_manager = sequence_manager

    def execute_steps(self, steps: Iterable[Step]):
        context = StepContext()

        for step in steps:
            context = self.run_step(step, context)

    @functools.singledispatchmethod
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

    #
    # @run_step.register
    # def _(
    #     self,
    #     linspace_loop: LinspaceLoop,
    #     context: StepContext,
    # ):
    #     """Loop over a variable in a numpy linspace like loop"""
    #
    #     variables = context.variables | units
    #
    #     try:
    #         start = Quantity(linspace_loop.start.evaluate(variables))
    #     except Exception as error:
    #         raise ValueError(
    #             f"Could not evaluate start of linspace loop {linspace_loop.name}"
    #         ) from error
    #     unit = start.units
    #     try:
    #         stop = Quantity(linspace_loop.stop.evaluate(variables))
    #     except Exception as error:
    #         raise ValueError(
    #             f"Could not evaluate stop of linspace loop {linspace_loop.name}"
    #         ) from error
    #     try:
    #         stop = stop.to(unit)
    #     except DimensionalityError:
    #         raise ValueError(
    #             f"Stop units of linspace loop '{linspace_loop.name}' ({stop.units}) is"
    #             f" not compatible with start units ({unit})"
    #         )
    #     num = int(linspace_loop.num)
    #
    #     for value in np.linspace(start.magnitude, stop.magnitude, num):
    #         context = context.update_variable(linspace_loop.name, value * unit)
    #         for step in linspace_loop.children:
    #             context = self.run_step(step, context)
    #     return context
    #
    @run_step.register
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
