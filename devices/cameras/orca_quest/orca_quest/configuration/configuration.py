from __future__ import annotations

from typing import TYPE_CHECKING

import attrs

from caqtus.device import DeviceName
from caqtus.device.camera import (
    CameraConfiguration,
    CameraUpdateParams,
)
from caqtus.shot_compilation import ShotContext
from caqtus.utils import serialization

if TYPE_CHECKING:
    # We avoid importing the runtime module because it imports the dcam dependency that
    # might not be installed in the current environment.
    # noinspection PyUnresolvedReferences
    from ..runtime import OrcaQuestCamera


@attrs.define
class OrcaQuestCameraConfiguration(CameraConfiguration["OrcaQuestCamera"]):
    """Holds the configuration for an OrcaQuest camera.

    Attributes:
        camera_number: The number of the camera to use.
    """

    camera_number: int = attrs.field(converter=int, on_setattr=attrs.setters.convert)

    def get_device_initialization_method(self, device_name, sequence_context):
        return (
            super()
            .get_device_initialization_method(device_name, sequence_context)
            .with_extra_parameters(name=device_name, camera_number=self.camera_number)
        )

    def compile_device_shot_parameters(
        self,
        device_name: DeviceName,
        shot_context: ShotContext,
    ) -> CameraUpdateParams:
        return super().compile_device_shot_parameters(device_name, shot_context)

    @classmethod
    def dump(cls, config: OrcaQuestCameraConfiguration) -> serialization.JSON:
        return serialization.unstructure(config)

    @classmethod
    def load(cls, data: serialization.JSON) -> OrcaQuestCameraConfiguration:
        return serialization.structure(data, OrcaQuestCameraConfiguration)
