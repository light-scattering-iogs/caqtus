from attrs import define, field

from .single_shot_viewer import SingleShotViewer


@define
class Workspace:
    viewers: dict[str, SingleShotViewer] = field(factory=dict)
