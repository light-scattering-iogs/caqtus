from collections.abc import Mapping, Iterable
from typing import Any

import attrs

from caqtus.device import DeviceName, DeviceConfiguration
from caqtus.session.shot import TimeLanes, TimeLane
from caqtus.types.variable_name import DottedVariableName
from .lane_compilers.timing import get_step_bounds
from ..types.expression import Expression
from ..types.parameter import is_quantity, magnitude_in_unit


@attrs.define(slots=False)
class ShotContext:
    """Contains information about a shot being compiled."""

    _time_lanes: TimeLanes
    _variables: Mapping[DottedVariableName, Any]

    _step_durations: tuple[float, ...] = attrs.field(init=False)
    _step_bounds: tuple[float, ...] = attrs.field(init=False)
    _was_lane_used: dict[str, bool] = attrs.field(init=False)

    def __attrs_post_init__(self):
        self._step_durations = tuple(
            evaluate_step_durations(
                self._time_lanes.step_names,
                self._time_lanes.step_durations,
                self._variables,
            )
        )
        self._step_bounds = tuple(get_step_bounds(self._step_durations))
        self._was_lane_used = {name: False for name in self._time_lanes.lanes}

    def get_lane(self, name: str) -> TimeLane:
        """Returns the lane with the given name for the shot.

        raises:
            KeyError: If no lane with the given name is present for the shot.
        """

        result = self._time_lanes.lanes[name]
        self._was_lane_used[name] = True
        return result

    def get_step_names(self) -> tuple[str, ...]:
        """Returns the names of the steps in the shot."""

        return tuple(self._time_lanes.step_names)

    def get_step_durations(self) -> tuple[float, ...]:
        """Returns the durations of each step in seconds."""

        return self._step_durations

    def get_step_bounds(self) -> tuple[float, ...]:
        """Returns the bounds of each step in seconds."""

        return self._step_bounds

    def get_shot_duration(self) -> float:
        """Returns the total duration of the shot in seconds."""

        return self._step_bounds[-1]

    def get_variables(self) -> Mapping[DottedVariableName, Any]:
        raise NotImplementedError

    def get_device_config(self, device_name: DeviceName) -> DeviceConfiguration:
        raise NotImplementedError

    def get_shot_parameters(self, device_name: DeviceName) -> Mapping[str, Any]:
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


def evaluate_step_durations(
    step_names: Iterable[str],
    step_durations: Iterable[Expression],
    variables: Mapping[DottedVariableName, Any],
) -> list[float]:
    result = []

    for name, duration in zip(step_names, step_durations):
        try:
            evaluated = duration.evaluate(variables)
        except Exception as e:
            raise ValueError(
                f"Couldn't evaluate duration <{duration}> of step <{name}>"
            ) from e

        if not is_quantity(evaluated):
            raise TypeError(
                f"Duration <{duration}> of step <{name}> is not a quantity "
                f"({evaluated})"
            )

        try:
            seconds = magnitude_in_unit(evaluated, "s")
        except Exception as error:
            raise ValueError(
                f"Duration <{duration}> of step <{name}> can't be converted to seconds "
                f"({evaluated})"
            ) from error
        if seconds < 0:
            raise ValueError(
                f"Duration <{duration}> of step <{name}> is negative ({seconds})"
            )
        result.append(float(seconds))
    return result
