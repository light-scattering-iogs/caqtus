"""Provides a widget for editing time lanes.

The main class is :class:`TimeLanesEditor` which is a widget that displays multiple
time lanes, along with the time steps, in a table-like view.

To know how to display and edit a specific type of lane, the editor uses
the :class:`extension.CondetrolLaneExtensionProtocol` to know how to build a
:class:`TimeLaneModel` and a :class:`TimeLaneDelegate` for each lane.
"""

from . import digital_lane_editor, analog_lane_editor, camera_lane_editor, extension
from ._delegate import TimeLaneDelegate
from ._time_lanes_editor import TimeLanesEditor
from ._time_lane_model import TimeLaneModel

__all__ = [
    "TimeLanesEditor",
    "digital_lane_editor",
    "analog_lane_editor",
    "camera_lane_editor",
    "TimeLaneModel",
    "TimeLaneDelegate",
    "extension",
]
