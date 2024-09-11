import attrs

from caqtus.types.data import DataLabel
from ._shot_id import ShotId


@attrs.frozen
class DataId:
    """Represents a unique identifier for data in the session.

    This is used to identify data in the session and is unique for each data.

    Attributes:
        shot_id: The shot to which the data belongs.
        data_label: The label of the data.
    """

    shot_id: ShotId
    data_label: DataLabel
