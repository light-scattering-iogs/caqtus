import abc
from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget

import qabc
from core.session.sequence.iteration_configuration import IterationConfiguration


class SequenceIterationEditor[T: IterationConfiguration](QWidget, qabc.QABC):
    iteration_changed = pyqtSignal()

    def __init__(self, iteration: T, parent: Optional[QWidget] = None):
        super().__init__(parent)

    @abc.abstractmethod
    def get_iteration(self) -> T:
        raise NotImplementedError

    @abc.abstractmethod
    def set_iteration(self, iteration: T):
        raise NotImplementedError
