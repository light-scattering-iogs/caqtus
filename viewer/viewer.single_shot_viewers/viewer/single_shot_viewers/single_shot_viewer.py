from typing import Protocol

from sequence.runtime import Shot


class SingleShotViewer(Protocol):
    def set_shot(self, shot: Shot) -> None:
        ...
