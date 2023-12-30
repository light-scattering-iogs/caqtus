import logging
from functools import singledispatchmethod
from threading import Thread, Event
from typing import assert_never

import numpy as np

from core.configuration.sequence import (
    Step,
    SequenceSteps,
    ArangeLoop,
    LinspaceLoop,
    VariableDeclaration,
    ExecuteShot,
)
from core.session import ExperimentSessionMaker, PureSequencePath
from core.types import AnalogValue
from core.types.units import Quantity, units, DimensionalityError
from .sequence_context import StepContext
from .sequence_manager import SequenceManager, SequenceInterruptedException

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SequenceRunnerThread(Thread):
    def __init__(
        self,
        experiment_config_name: str,
        sequence_path: PureSequencePath,
        session_maker: ExperimentSessionMaker,
        must_interrupt: Event,
    ):
        super().__init__(name=f"thread_{str(sequence_path)}")
        self._sequence_manager = SequenceManager(
            experiment_config_name, sequence_path, session_maker, must_interrupt
        )

    def run(self):
        try:
            with self._sequence_manager:
                self.run_sequence()
        except* SequenceInterruptedException:
            pass
        except* Exception:
            logger.error("An error occurred while running the sequence", exc_info=True)
            raise

    def run_sequence(self):
        """Run the sequence.

        This function will first run the sequence header used to populate the context with constants, then it will run
        the sequence program containing the shots.
        """

        context = StepContext[AnalogValue]()

        context = self.run_step(
            self._sequence_manager.experiment_config.header, context
        )
        _ = self.run_step(self._sequence_manager.sequence_config.program, context)

    @singledispatchmethod
    def run_step(self, step: Step, context: StepContext) -> StepContext:
        """Execute a given step of the sequence

        This function should be implemented for each Step type that can be run on the
        experiment.

        Args:
            step: the step of the sequence currently executed
            context: Contains the values of the variables before this step.

        Returns:
            A new context object that contains the values of the variables after this step. This context object must be
            a new object.
        """

        return assert_never(step)

    @run_step.register
    def _(
        self,
        steps: SequenceSteps,
        context: StepContext,
    ) -> StepContext:
        """Execute the steps of a SequenceSteps.

        This function executes the child steps of a SequenceSteps in order. The context is updated after each step and
        the updated context is passed to the next step.
        """

        for step in steps.children:
            context = self.run_step(step, context)
        return context

    @run_step.register
    def _(
        self,
        declaration: VariableDeclaration,
        context: StepContext,
    ) -> StepContext:
        """Execute a VariableDeclaration step.

        This function evaluates the expression of the declaration and updates the value of the variable in the context.
        """

        value = Quantity(declaration.expression.evaluate(context.variables | units))
        return context.update_variable(declaration.name, value)

    @run_step.register
    def _(
        self,
        arange_loop: ArangeLoop,
        context: StepContext,
    ):
        """Loop over a variable in a numpy arange like loop"""

        variables = context.variables | units

        start = Quantity(arange_loop.start.evaluate(variables))
        stop = Quantity(arange_loop.stop.evaluate(variables))
        step = Quantity(arange_loop.step.evaluate(variables))
        unit = start.units

        start = start.to(unit)
        try:
            stop = stop.to(unit)
        except DimensionalityError:
            raise ValueError(
                f"Stop units of arange loop '{arange_loop.name}' ({stop.units}) is not"
                f" compatible with start units ({unit})"
            )
        try:
            step = step.to(unit)
        except DimensionalityError:
            raise ValueError(
                f"Step units of arange loop '{arange_loop.name}' ({step.units}) are not"
                f" compatible with start units ({unit})"
            )

        for value in np.arange(start.magnitude, stop.magnitude, step.magnitude):
            context = context.update_variable(arange_loop.name, value * unit)
            for step in arange_loop.children:
                context = self.run_step(step, context)
        return context

    @run_step.register
    def _(
        self,
        linspace_loop: LinspaceLoop,
        context: StepContext,
    ):
        """Loop over a variable in a numpy linspace like loop"""

        variables = context.variables | units

        try:
            start = Quantity(linspace_loop.start.evaluate(variables))
        except Exception as error:
            raise ValueError(
                f"Could not evaluate start of linspace loop {linspace_loop.name}"
            ) from error
        unit = start.units
        try:
            stop = Quantity(linspace_loop.stop.evaluate(variables))
        except Exception as error:
            raise ValueError(
                f"Could not evaluate stop of linspace loop {linspace_loop.name}"
            ) from error
        try:
            stop = stop.to(unit)
        except DimensionalityError:
            raise ValueError(
                f"Stop units of linspace loop '{linspace_loop.name}' ({stop.units}) is"
                f" not compatible with start units ({unit})"
            )
        num = int(linspace_loop.num)

        for value in np.linspace(start.magnitude, stop.magnitude, num):
            context = context.update_variable(linspace_loop.name, value * unit)
            for step in linspace_loop.children:
                context = self.run_step(step, context)
        return context

    @run_step.register
    def _(self, shot: ExecuteShot, context: StepContext) -> StepContext:
        """Compute the parameters of a shot and push them to the queue to be executed."""

        logger.debug(context.variables)

        self._sequence_manager.schedule_shot(shot.name, context)
        return context.reset_history()
