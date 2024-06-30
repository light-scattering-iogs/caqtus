from collections.abc import Mapping, Iterable
from typing import Any, TypeVar, TYPE_CHECKING

import attrs

from caqtus.device import DeviceName, DeviceConfiguration
from caqtus.session.shot import TimeLanes, TimeLane
from caqtus.types.variable_name import DottedVariableName
from .lane_compilers.timing import get_step_bounds
from ..formatter import fmt
from ..types.expression import Expression
from ..types.parameter import is_quantity, magnitude_in_unit

if TYPE_CHECKING:
    from caqtus.shot_compilation import DeviceCompiler

LaneType = TypeVar("LaneType", bound=TimeLane)


@attrs.define(slots=False)
class SequenceContext:
    """Contains information about a sequence being compiled."""

    _device_configurations: Mapping[DeviceName, DeviceConfiguration]
    _time_lanes: TimeLanes

    def get_device_configuration(self, device_name: DeviceName) -> DeviceConfiguration:
        """Returns the configuration for the given device.

        raises:
            KeyError: If no configuration is found for the given device.
        """

        return self._device_configurations[device_name]

    def get_all_device_configurations(self) -> Mapping[DeviceName, DeviceConfiguration]:
        """Returns all device configurations available in this sequence."""

        return self._device_configurations

    def get_lane(self, name: str) -> TimeLane:
        """Returns the time lane with the given name.

        raises:
            KeyError: If no lane with the given name is not found in the sequence
            context.
        """

        return self._time_lanes.lanes[name]

    def get_lanes_with_type(self, lane_type: type[LaneType]) -> Mapping[str, LaneType]:
        """Returns the lanes used during the shot with the given type."""

        return {
            name: lane
            for name, lane in self._time_lanes.lanes.items()
            if isinstance(lane, lane_type)
        }

    def get_step_names(self) -> tuple[str, ...]:
        """Returns the names of the steps in the sequence."""

        return tuple(self._time_lanes.step_names)


@attrs.define
class ShotContext:
    """Contains information about a shot being compiled."""

    _sequence_context: SequenceContext
    _variables: Mapping[DottedVariableName, Any]
    _device_compilers: Mapping[DeviceName, "DeviceCompiler"]

    _step_durations: tuple[float, ...] = attrs.field(init=False)
    _step_bounds: tuple[float, ...] = attrs.field(init=False)
    _was_lane_used: dict[str, bool] = attrs.field(init=False)
    _computed_shot_parameters: dict[DeviceName, Mapping[str, Any]] = attrs.field(
        init=False
    )

    @property
    def _time_lanes(self) -> TimeLanes:
        # noinspection PyProtectedMember
        return self._sequence_context._time_lanes

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
        self._computed_shot_parameters = {}

    def get_lane(self, name: str) -> TimeLane:
        """Returns the lane with the given name for the shot.

        raises:
            KeyError: If no lane with the given name is present for the shot.
        """

        lane = self._sequence_context.get_lane(name)
        self._was_lane_used[name] = True
        return lane

    def get_lanes_with_type(self, lane_type: type[LaneType]) -> Mapping[str, LaneType]:
        """Returns the lanes used during the shot with the given type."""

        # Unclear if the lanes obtained here should be marked as used or not.
        return self._sequence_context.get_lanes_with_type(lane_type)

    def get_step_names(self) -> tuple[str, ...]:
        """Returns the names of the steps in the shot."""

        return self._sequence_context.get_step_names()

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
        """Returns the variables for the shot."""

        return self._variables

    def get_device_config(self, device_name: DeviceName) -> DeviceConfiguration:
        """Returns the configuration for the given device.

        raises:
            KeyError: If no configuration is found for the given device.
        """

        return self._sequence_context.get_device_configuration(device_name)

    def get_shot_parameters(self, device_name: DeviceName) -> Mapping[str, Any]:
        """Returns the parameters computed for the given device."""

        if device_name in self._computed_shot_parameters:
            return self._computed_shot_parameters[device_name]
        else:
            compiler = self._device_compilers[device_name]
            shot_parameters = compiler.compile_shot_parameters(self)
            self._computed_shot_parameters[device_name] = shot_parameters
            return shot_parameters

    def _unused_lanes(self) -> set[str]:
        return {name for name, used in self._was_lane_used.items() if not used}


def evaluate_step_durations(
    step_names: Iterable[str],
    step_durations: Iterable[Expression],
    variables: Mapping[DottedVariableName, Any],
) -> list[float]:
    result = []

    for step, (name, duration) in enumerate(zip(step_names, step_durations)):
        try:
            evaluated = duration.evaluate(variables)
        except Exception as e:
            raise ValueError(
                fmt(
                    "Couldn't evaluate {:expression} for duration of {:step}",
                    duration,
                    (step, name),
                )
            ) from e

        if not is_quantity(evaluated):
            raise TypeError(
                fmt(
                    "{:expression} for duration of {:step} does not evaluate "
                    "to a quantity",
                    duration,
                    (step, name),
                )
            )

        try:
            seconds = magnitude_in_unit(evaluated, "s")
        except Exception as error:
            raise ValueError(
                fmt(
                    "Couldn't convert {:expression} for duration of {:step} to "
                    "seconds",
                    duration,
                    (step, name),
                )
            ) from error
        if seconds < 0:
            raise ValueError(
                fmt(
                    "{:expression} for duration of {:step} is negative",
                    duration,
                    (step, name),
                )
            )
        result.append(float(seconds))
    return result
