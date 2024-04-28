from typing import Any

import attrs

from caqtus.utils.serialization import JSON
from ..single_shot_viewers import ManagerName


@attrs.define
class ViewState:
    view_state: JSON
    window_geometry: str
    window_state: str


@attrs.define
class WorkSpace:
    window_state: str
    window_geometry: str
    view_states: dict[str, ViewState]
