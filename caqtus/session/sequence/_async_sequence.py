from __future__ import annotations

import asyncio
import datetime
from collections.abc import Iterable, Callable, AsyncIterable, Coroutine, Awaitable
from typing import Optional

import attrs
import polars

from caqtus.types.variable_name import DottedVariableName
from .iteration_configuration import IterationConfiguration, Unknown
from .state import State
from .. import AsyncExperimentSession
from .._return_or_raise import unwrap
from ..parameter_namespace import ParameterNamespace
from ..path import PureSequencePath
from ..shot import AsyncShot
from ..shot import TimeLanes


def _convert_to_path(path: PureSequencePath | str) -> PureSequencePath:
    if isinstance(path, str):
        return PureSequencePath(path)
    return path


@attrs.frozen(eq=False, order=False)
class AsyncSequence:
    """Asynchronous version of :class:`Sequence`."""

    path: PureSequencePath = attrs.field(converter=_convert_to_path)
    session: AsyncExperimentSession

    def __str__(self) -> str:
        return str(self.path)

    async def get_state(self) -> State:
        return unwrap(await self.session.sequences.get_state(self.path))

    async def get_global_parameters(self) -> ParameterNamespace:
        return await self.session.sequences.get_global_parameters(self.path)

    async def get_iteration_configuration(self) -> IterationConfiguration:
        return await self.session.sequences.get_iteration_configuration(self.path)

    async def get_time_lanes(self) -> TimeLanes:
        return await self.session.sequences.get_time_lanes(self.path)

    async def get_shots(self) -> list[AsyncShot]:
        pure_shots = unwrap(await self.session.sequences.get_shots(self.path))
        return [AsyncShot.bound(shot, self.session) for shot in pure_shots]

    async def get_start_time(self) -> Optional[datetime.datetime]:
        return unwrap(await self.session.sequences.get_stats(self.path)).start_time

    async def get_end_time(self) -> Optional[datetime.datetime]:
        return unwrap(await self.session.sequences.get_stats(self.path)).stop_time

    async def get_expected_number_of_shots(self) -> int | Unknown:
        return unwrap(
            await self.session.sequences.get_stats(self.path)
        ).expected_number_shots

    async def get_local_parameters(self) -> set[DottedVariableName]:
        iterations = await self.get_iteration_configuration()
        return iterations.get_parameter_names()

    def load_shots_data(
        self,
        importer: Callable[[AsyncShot], Coroutine[None, None, polars.DataFrame]],
        tags: Optional[polars.type_aliases.FrameInitTypes] = None,
    ) -> Iterable[polars.DataFrame]:
        async def to_list():
            result = []
            async for df in self.load_shots_data_async(importer, tags):
                result.append(df)
            return result

        return asyncio.run(to_list())

    async def load_shots_data_async(
        self,
        importer: Callable[[AsyncShot], Awaitable[polars.DataFrame]],
        tags: Optional[polars.type_aliases.FrameInitTypes] = None,
    ) -> AsyncIterable[polars.DataFrame]:
        shots = await self.get_shots()
        shots.sort(key=lambda x: x.index)
        if tags is not None:
            tags_dataframe = polars.DataFrame(tags)
            if len(tags_dataframe) != 1:
                raise ValueError("tags should be a single row DataFrame")
        else:
            tags_dataframe = None

        for shot in shots:
            data = await importer(shot)

            if tags is not None:
                yield data.join(tags_dataframe, how="cross")
            else:
                yield data
