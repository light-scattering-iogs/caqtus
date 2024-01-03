from typing import Optional

from PyQt6.QtWidgets import QWidget, QTreeView

from core.session.sequence.iteration_configuration import StepsConfiguration
from ..sequence_iteration_editor import SequenceIterationEditor
from .steps_model import StepsModel


class StepsIterationEditor(QTreeView, SequenceIterationEditor[StepsConfiguration]):
    def __init__(self, iteration: StepsConfiguration, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.iteration = iteration
        self.read_only = False
        self._model = StepsModel(iteration)
        self.setModel(self._model)
        self.expandAll()
        self.header().hide()

    def get_iteration(self) -> StepsConfiguration:
        return self.iteration

    def set_iteration(self, iteration: StepsConfiguration):
        self.iteration = iteration

    def set_read_only(self, read_only: bool):
        self.read_only = read_only
