from __future__ import annotations

from abc import abstractmethod
from typing import Optional, TypeVar, Generic, Callable, NewType

import attrs
from PyQt6.QtWidgets import QWidget

from core.session.sequence import Shot
from qabc import QABC
from util.serialization import JSON


class ShotView(QWidget, QABC):
    @abstractmethod
    def display_shot(self, shot: Shot) -> None:
        raise NotImplementedError


S = TypeVar("S", bound=JSON)
V = TypeVar("V", bound=ShotView)

ManagerName = NewType("ManagerName", str)


@attrs.define
class ViewManager(Generic[V, S]):
    constructor: Callable[[S], V]
    dumper: Callable[[V], S]
    state_generator: Callable[[QWidget], Optional[tuple[str, S]]]
