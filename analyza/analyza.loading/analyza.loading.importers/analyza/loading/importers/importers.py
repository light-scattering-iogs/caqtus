from datetime import datetime
from typing import (
    Any,
    TypeVar,
    ParamSpec,
    TypedDict,
)

from atom_detector.configuration import AtomLabel
from data_types import Data
from device.configuration import DeviceName
from experiment.session import ExperimentSession
from image_types import Image, is_image, ImageLabel
from parameter_types import Parameter
from sequence.runtime import Shot
from .chainable_function import ChainableFunction
from .shot_importer import ShotImporter

P = ParamSpec("P")
S = TypeVar("S")
T = TypeVar("T")

K = TypeVar("K")
V = TypeVar("V")


class ImageImporter(ShotImporter[Image]):
    def __init__(self, camera_name: DeviceName, image: ImageLabel):
        self.camera_name = camera_name
        self.image = image

    def __call__(self, shot: Shot, session: ExperimentSession) -> Image:
        value = _import_measures(shot, session)[f"{self.camera_name}.{self.image}"]
        if not is_image(value):
            raise TypeError(
                f"Expected image for {self.camera_name}.{self.image}, got {type(value)}"
            )
        return value


class AtomsImporter(ShotImporter[dict[AtomLabel, bool]]):
    def __init__(self, detector: DeviceName, image: ImageLabel):
        self.detector = detector
        self.image = image

    def __call__(self, shot: Shot, session: ExperimentSession) -> dict[AtomLabel, bool]:
        value = _import_measures(shot, session)[f"{self.detector}.{self.image}"]
        if not isinstance(value, dict):
            raise TypeError(
                f"Expected dictionary for {self.detector}.{self.image}, got {type(value)}"
            )
        return value


def _import_parameters(shot: Shot, session: ExperimentSession) -> dict[str, Parameter]:
    return {
        str(name): parameter for name, parameter in shot.get_parameters(session).items()
    }


def _import_scores(shot: Shot, session: ExperimentSession) -> dict[str, Any]:
    scores = shot.get_scores(session)
    return {f"{key}.score": value for key, value in scores.items()}


def _import_measures(shot: Shot, session: ExperimentSession) -> dict[str, Data]:
    result = {}
    data = shot.get_measures(session)
    for device, device_data in data.items():
        for key, value in device_data.items():
            result[f"{device}.{key}"] = value
    return result


class _ImportTimeResult(TypedDict):
    start_time: datetime
    end_time: datetime


def _import_time(shot: Shot, session: ExperimentSession) -> _ImportTimeResult:
    return _ImportTimeResult(
        start_time=shot.get_start_time(session), end_time=shot.get_end_time(session)
    )


def _import_all(shot: Shot, session: ExperimentSession) -> dict[str, Any]:
    return dict(
        **_import_time(shot, session),
        **_import_scores(shot, session),
        **_import_parameters(shot, session),
        **_import_measures(shot, session),
    )


import_all = ChainableFunction(_import_all)
import_parameters = ChainableFunction(_import_parameters)
import_scores = ChainableFunction(_import_scores)
import_measures = ChainableFunction(_import_measures)
import_time = ChainableFunction(_import_time)
