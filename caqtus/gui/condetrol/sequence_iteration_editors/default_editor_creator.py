import functools
from typing import TypeVar

from caqtus.types.iteration import (
    IterationConfiguration,
    StepsConfiguration,
)

from .sequence_iteration_editor import SequenceIterationEditor
from .steps_iteration_editor import StepsIterationEditor

T = TypeVar("T", bound=IterationConfiguration)


@functools.singledispatch
def create_default_editor(iteration: T) -> SequenceIterationEditor[T]:
    raise NotImplementedError


@create_default_editor.register
def _(iteration: StepsConfiguration) -> SequenceIterationEditor[StepsConfiguration]:
    return StepsIterationEditor(iteration)
