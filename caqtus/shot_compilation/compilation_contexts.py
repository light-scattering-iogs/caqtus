from collections.abc import Mapping
from typing import Any

import attrs

from caqtus.device import DeviceName, DeviceConfiguration
from caqtus.session.shot import TimeLanes, TimeLane
from caqtus.types.variable_name import DottedVariableName


@attrs.define(slots=False)
class ShotContext:
    def get_lane(self, name: str) -> TimeLane:
        """Returns the lane with the given name for the shot.

        raises:
            KeyError: If no lane with the given name is present for the shot.
        """

        raise NotImplementedError

    def get_step_durations(self) -> list[float]:
        raise NotImplementedError

    def get_shot_duration(self) -> float:
        raise NotImplementedError

    def get_variables(self) -> Mapping[DottedVariableName, Any]:
        raise NotImplementedError


@attrs.define(slots=False)
class SequenceContext:
    def get_device_configurations(self) -> Mapping[DeviceName, DeviceConfiguration]:
        raise NotImplementedError

    def get_time_lanes(self) -> TimeLanes:
        raise NotImplementedError

    def get_lane(self, name: str) -> TimeLane:
        """Returns the time lane with the given name.

        raises:
            KeyError: If no lane with the given name is not found in the sequence
            context.
        """
        raise NotImplementedError
