from abc import abstractmethod

from PyQt6.QtWidgets import QWidget

from qabc import QABC
from sequence.runtime import Shot


class SingleShotViewer(QWidget, QABC):
    @abstractmethod
    def set_shot(self, shot: Shot) -> None:
        ...
