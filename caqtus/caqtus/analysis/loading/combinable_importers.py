import abc
from collections.abc import Sequence

import polars

from caqtus.session import Shot, ExperimentSession


class CombinableLoader(abc.ABC):
    @abc.abstractmethod
    def __call__(self, shot: Shot, session: ExperimentSession) -> polars.DataFrame:
        ...

    def __add__(self, other):
        if isinstance(other, CombinableLoader):
            return HorizontalConcatenateLoader(self, other)
        else:
            return NotImplemented

    def __mul__(self, other):
        if isinstance(other, CombinableLoader):
            return CrossProductLoader(self, other)
        else:
            return NotImplemented


class HorizontalConcatenateLoader(CombinableLoader):
    def __init__(self, *loaders: CombinableLoader):
        self.loaders = []
        for loader in loaders:
            if isinstance(loader, HorizontalConcatenateLoader):
                self.loaders.extend(loader.loaders)
            else:
                self.loaders.append(loader)

    def __call__(self, shot: Shot, session: ExperimentSession) -> polars.DataFrame:
        return polars.concat(
            [loader(shot, session) for loader in self.loaders], how="horizontal"
        )


class CrossProductLoader(CombinableLoader):
    def __init__(self, first: CombinableLoader, second: CombinableLoader):
        self.first = first
        self.second = second

    def __call__(self, shot: Shot, session: ExperimentSession) -> polars.DataFrame:
        return self.first(shot, session).join(self.second(shot, session), how="cross")


# noinspection PyPep8Naming
class join(CombinableLoader):
    def __init__(self, *loaders: CombinableLoader, on: Sequence[str]):
        if len(loaders) < 1:
            raise ValueError("At least one loader must be provided.")
        self.loaders = loaders
        self.on = on

    def __call__(self, shot: Shot, session: ExperimentSession) -> polars.DataFrame:
        dataframe = self.loaders[0](shot, session)
        for loader in self.loaders[1:]:
            dataframe = dataframe.join(loader(shot, session), on=self.on, how="inner")
        return dataframe
