from datetime import datetime
from typing import (
    Any,
    TypeVar,
    ParamSpec,
    TypedDict,
    TypeGuard,
)

from atom_detector.configuration import AtomLabel
from data_types import Data
from device.configuration import DeviceName
from experiment.session import ExperimentSession
from image_types import Image, is_image, ImageLabel
from parameter_types import Parameter
from sequence.runtime import Shot
from util import attrs, serialization
from . import break_namespaces
from .chainable_function import ChainableFunction
from .shot_importer import (
    ShotImporter,
    ImageImporter,
    ParametersImporter,
    AtomImporter2D,
)

P = ParamSpec("P")
S = TypeVar("S")
T = TypeVar("T")

K = TypeVar("K")
V = TypeVar("V")


@attrs.define
class ImageLoader(ImageImporter):
    camera_name: DeviceName = attrs.field()
    image: ImageLabel = attrs.field()

    def __call__(self, shot: Shot, session: ExperimentSession) -> Image:
        value = shot.get_data_by_label(self.camera_name, session)[self.image]
        if not is_image(value):
            raise TypeError(
                f"Expected image for {self.camera_name}.{self.image}, got {type(value)}"
            )
        return value


serialization.include_subclasses(
    ImageImporter, union_strategy=serialization.include_type()
)


@attrs.define
class ParametersLoader(ParametersImporter):
    def __attrs_post_init__(self) -> None:
        self._importer = import_parameters | break_namespaces

    def __call__(self, shot: Shot, session: ExperimentSession) -> dict[str, Parameter]:
        return self._importer(shot, session)


serialization.include_subclasses(
    ParametersImporter, union_strategy=serialization.include_type()
)


@attrs.define
class AtomsLoader(ShotImporter[dict[AtomLabel, bool]]):
    detector_name: DeviceName = attrs.field(converter=str)
    image: ImageLabel = attrs.field(converter=str)
    check_return_type: bool = attrs.field(default=False, converter=bool)

    def __call__(self, shot: Shot, session: ExperimentSession) -> dict[AtomLabel, bool]:
        value = shot.get_data_by_label(self.detector_name, session)[self.image]
        if self.check_return_type:
            if not self._check_return_type(value):
                raise TypeError(
                    f"Expected dict[AtomLabel, bool] for {self.detector_name}.{self.image}, got {type(value)}"
                )
        return value

    @staticmethod
    def _check_return_type(value: Any) -> TypeGuard[dict[AtomLabel, bool]]:
        if not isinstance(value, dict):
            return False
        for key, value in value.items():
            if not isinstance(key, AtomLabel):
                return False
            if not isinstance(value, bool):
                return False
        return True


class AtomsLoader2D(AtomsLoader, AtomImporter2D):
    pass


serialization.include_subclasses(
    AtomImporter2D, union_strategy=serialization.include_type()
)


def _import_parameters(shot: Shot, session: ExperimentSession) -> dict[str, Parameter]:
    parameters = list(shot.get_parameters(session).items())
    parameters.sort(key=lambda item: str(item[0]))
    return {str(name): value for name, value in parameters}


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
