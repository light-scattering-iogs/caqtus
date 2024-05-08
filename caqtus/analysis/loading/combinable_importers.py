import abc
from collections.abc import Sequence, Iterable

import polars

from caqtus.session import Shot
from caqtus.session.shot import AsyncShot
from .shot_data import DataImporter


class CombinableLoader(DataImporter, abc.ABC):
    """A loader that can be combined with other loaders.

    Objects that inherit from this class can be combined with other loaders using the
    `+` and `*` operators.
    The `+` operator will concatenate the dataframes returned by the loaders.
    The `*` operator will perform a cross product of the dataframes returned by the
    loaders.
    """

    def __call__(self, shot: Shot) -> polars.DataFrame:
        return self.load(shot)

    @abc.abstractmethod
    def load(self, shot: Shot) -> polars.DataFrame: ...

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

    @staticmethod
    def _concatenate(dataframes: Iterable[polars.DataFrame]) -> polars.DataFrame:
        return polars.concat(dataframes, how="horizontal")

    def load(self, shot: Shot) -> polars.DataFrame:
        return self._concatenate(loader(shot) for loader in self.loaders)


class CrossProductLoader(CombinableLoader):
    def __init__(self, first: CombinableLoader, second: CombinableLoader):
        self.first = first
        self.second = second

    @staticmethod
    def _join(first: polars.DataFrame, second: polars.DataFrame) -> polars.DataFrame:
        return first.join(second, how="cross")

    def load(self, shot: Shot) -> polars.DataFrame:
        return self._join(self.first(shot), self.second(shot))


# noinspection PyPep8Naming
class join(CombinableLoader):
    """Join multiple loaders on given columns."""

    def __init__(self, *loaders: CombinableLoader, on: Sequence[str]):
        if len(loaders) < 1:
            raise ValueError("At least one loader must be provided.")
        self.loaders = loaders
        self.on = on

    def _join(self, dataframes: Sequence[polars.DataFrame]) -> polars.DataFrame:
        dataframe = dataframes[0]
        for other in dataframes[1:]:
            dataframe = dataframe.join(other, on=self.on, how="inner")
        return dataframe

    def load(self, shot: Shot) -> polars.DataFrame:
        return self._join([loader(shot) for loader in self.loaders])
