import abc
from collections.abc import Callable
from typing import TypeVar, Generic, TypeAlias

import caqtus.gui.qtutil.qabc as qabc
from PySide6.QtCore import Signal
from caqtus.types.iteration import IterationConfiguration

T = TypeVar("T", bound=IterationConfiguration)


class SequenceIterationEditor(Generic[T], metaclass=qabc.QABCMeta):
    iteration_edited = Signal(IterationConfiguration)

    @abc.abstractmethod
    def get_iteration(self) -> T:
        raise NotImplementedError

    @abc.abstractmethod
    def set_iteration(self, iteration: T):
        raise NotImplementedError

    @abc.abstractmethod
    def set_read_only(self, read_only: bool):
        raise NotImplementedError


IterationEditorCreator: TypeAlias = Callable[[T], SequenceIterationEditor[T]]
