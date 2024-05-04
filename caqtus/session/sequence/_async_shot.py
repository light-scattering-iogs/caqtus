from __future__ import annotations

import datetime
import typing
from collections.abc import Mapping

import attrs

from caqtus.types.data import DataLabel, Data
from caqtus.types.parameter import Parameter
from caqtus.types.variable_name import DottedVariableName
from ..path import PureSequencePath
from ..sequence import AsyncSequence
from ..sequence_collection import PureShot

if typing.TYPE_CHECKING:
    from ..async_session import AsyncExperimentSession


@attrs.frozen(eq=False, order=False)
class AsyncShot:
    """An async version of :class:`Shot`."""

    sequence_path: PureSequencePath
    index: int
    _session: "AsyncExperimentSession"

    @classmethod
    def bound(cls, shot: PureShot, session: AsyncExperimentSession) -> typing.Self:
        return cls(shot.sequence_path, shot.index, session)

    @property
    def sequence(self) -> AsyncSequence:
        return AsyncSequence(self.sequence_path, self._session)

    async def get_parameters(self) -> Mapping[DottedVariableName, Parameter]:
        return await self._session.sequences.get_shot_parameters(
            self.sequence_path, self.index
        )

    async def get_data(self) -> Mapping[DataLabel, Data]:
        return await self._session.sequences.get_all_shot_data(
            self.sequence_path, self.index
        )

    async def get_data_by_label(self, label: DataLabel) -> Data:
        return await self._session.sequences.get_shot_data_by_label(
            self.sequence_path, self.index, label
        )

    async def get_start_time(self) -> datetime.datetime:
        return await self._session.sequences.get_shot_start_time(
            self.sequence_path, self.index
        )

    async def get_end_time(self) -> datetime.datetime:
        return await self._session.sequences.get_shot_end_time(
            self.sequence_path, self.index
        )
