import abc
from collections.abc import Callable
from typing import TypeVar, Generic, TypeAlias

import qabc
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget
from core.session.sequence.iteration_configuration import IterationConfiguration

T = TypeVar("T", bound=IterationConfiguration)


class SequenceIterationEditor(QWidget, qabc.QABC, Generic[T]):
    iteration_changed = pyqtSignal()

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
