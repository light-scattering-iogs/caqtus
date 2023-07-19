import logging
from abc import ABC
from typing import Optional

from pydantic import validator

from settings_model import SettingsModel
from .lane import Lane

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class CameraAction(SettingsModel, ABC):
    pass


class TakePicture(CameraAction):
    picture_name: str


class CameraLane(Lane[Optional[CameraAction]]):
    """Lane to describe a camera

    The name of this lane must match one of the camera present in the experiment configuration.
    """

    @validator("values")
    def validate_values(cls, actions, values):
        """Check that there are not two separate pictures with the same name"""

        actions = super().validate_values(actions, values)
        spans = values["spans"]
        name = values["name"]
        picture_names = set()
        for action, span in zip(actions, spans):
            if span > 0 and isinstance(action, TakePicture):
                if action.picture_name in picture_names:
                    raise ValueError(
                        f"Picture name '{action.picture_name} is used twice in lane"
                        f" '{name}'"
                    )
                else:
                    picture_names.add(action.picture_name)
        return actions

    def get_picture_spans(self) -> list[tuple[str, int, int]]:
        """Return a list of the pictures and the step index at which they start (included) and stop (excluded)"""

        result = []
        for action, start, stop in self.get_value_spans():
            if isinstance(action, TakePicture):
                result.append((action.picture_name, start, stop))
        return result

    def get_picture_names(self) -> list[str]:
        return [name for name, _, _ in self.get_picture_spans()]
