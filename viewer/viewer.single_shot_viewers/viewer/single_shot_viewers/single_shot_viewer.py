from abc import abstractmethod
from typing import Protocol

from sequence.runtime import Shot


class SingleShotViewer(Protocol):
    @abstractmethod
    def set_shot(self, shot: Shot) -> None:
        ...
