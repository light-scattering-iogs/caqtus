from abc import abstractmethod

from PyQt6.QtWidgets import QWidget
from attrs import define

from qabc import QABC
from sequence.runtime import Shot


@define(init=False, slots=False)
class SingleShotViewer(QWidget, QABC):
    def __init__(self):
        super().__init__()

    @abstractmethod
    def set_shot(self, shot: Shot) -> None:
        raise NotImplementedError()

    @abstractmethod
    def update_view(self) -> None:
        raise NotImplementedError()
