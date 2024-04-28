from typing import Any

import attrs


@attrs.define
class ViewState:
    view_state: Any
    window_geometry: str


@attrs.define
class WorkSpace:
    window_state: str
    window_geometry: str
    view_states: dict[str, ViewState]
