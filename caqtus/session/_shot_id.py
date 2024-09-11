from __future__ import annotations

import attrs

from ._path import PureSequencePath


@attrs.frozen
class ShotId:
    """Unique identifier for a shot in a sequence."""

    sequence_path: PureSequencePath
    index: int
