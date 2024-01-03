import abc
from collections.abc import Callable

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget

import qabc
from core.session.sequence.iteration_configuration import IterationConfiguration


class SequenceIterationEditor[T: IterationConfiguration](QWidget, qabc.QABC):
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


type IterationEditorCreator[T: IterationConfiguration] = Callable[
    [T], SequenceIterationEditor[T]
]
