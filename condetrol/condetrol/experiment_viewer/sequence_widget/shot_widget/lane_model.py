from functools import singledispatch

from analog_lane.configuration import AnalogLane
from analog_lane.model import AnalogLaneModel
from atom_detector_lane.configuration import AtomDetectorLane
from atom_detector_lane.model.atom_detector_lane_model import AtomDetectorLaneModel
from camera_lane.configuration import CameraLane
from camera_lane.model import CameraLaneModel
from digital_lane.configuration import DigitalLane
from digital_lane.model import DigitalLaneModel
from experiment.configuration import ExperimentConfig
from expression import Expression
from lane.configuration import Lane
from tweezer_arranger.configuration import TweezerConfigurationName
from tweezer_arranger_lane.configuration import TweezerArrangerLane, HoldTweezers
from tweezer_arranger_lane.model.tweezer_arranger_lane_model import (
    TweezerArrangerLaneModel,
)


@singledispatch
def get_lane_model(lane: Lane, experiment_config: ExperimentConfig):
    match lane:
        case DigitalLane():
            return DigitalLaneModel(lane, experiment_config)
        case AnalogLane():
            return AnalogLaneModel(lane, experiment_config)
        case CameraLane():
            return CameraLaneModel(lane, experiment_config)
        case TweezerArrangerLane():
            return TweezerArrangerLaneModel(lane, experiment_config)
        case AtomDetectorLane():
            return AtomDetectorLaneModel(lane, experiment_config)
        case _:
            raise NotImplementedError(
                f"get_lane_model not implemented for {type(lane)} and {type(experiment_config)}"
            )


def create_new_lane(
    number_steps: int,
    lane_type: type[Lane],
    name: str,
    experiment_config: ExperimentConfig,
) -> Lane:
    if lane_type == DigitalLane:
        return DigitalLane(
            name=name,
            values=tuple(False for _ in range(number_steps)),
            spans=tuple(1 for _ in range(number_steps)),
        )
    elif lane_type == AnalogLane:
        return AnalogLane(
            name=name,
            values=tuple(Expression("...") for _ in range(number_steps)),
            spans=tuple(1 for _ in range(number_steps)),
            units=experiment_config.get_input_units(name),
        )
    elif lane_type == CameraLane:
        return CameraLane(
            name=name,
            values=(None,) * number_steps,
            spans=(1,) * number_steps,
        )
    elif lane_type == TweezerArrangerLane:
        return TweezerArrangerLane(
            name=name,
            values=(HoldTweezers(configuration=TweezerConfigurationName("...")),)
            * number_steps,
            spans=(number_steps,) + (0,) * (number_steps - 1),
        )
    elif lane_type == AtomDetectorLane:
        return AtomDetectorLane(
            name=name,
            values=(None,) * number_steps,
            spans=(number_steps,) + (0,) * (number_steps - 1),
        )
    else:
        raise NotImplementedError(f"create_new_lane not implemented for {lane_type}")
