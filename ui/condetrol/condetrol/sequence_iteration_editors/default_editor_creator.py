import functools

from core.session.sequence.iteration_configuration import (
    IterationConfiguration,
    StepsConfiguration,
)
from .sequence_iteration_editor import SequenceIterationEditor
from .steps_iteration_editor import StepsIterationEditor


@functools.singledispatch
def create_default_editor[
    T: IterationConfiguration
](iteration: T) -> SequenceIterationEditor[T]:
    raise NotImplementedError


@create_default_editor.register
def _(iteration: StepsConfiguration) -> SequenceIterationEditor[StepsConfiguration]:
    return StepsIterationEditor(iteration)
