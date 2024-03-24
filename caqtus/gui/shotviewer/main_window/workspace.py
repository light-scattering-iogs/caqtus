from typing import Any

import attrs

from ..single_shot_viewers import ManagerName


@attrs.define
class ViewState:
    manager_name: ManagerName
    view_state: Any


@attrs.define
class WorkSpace:
    window_state: str
    window_geometry: str
    docks_state: Any
    views: dict[str, ViewState]
