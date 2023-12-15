import abc

import polars
from core.session import Shot, ExperimentSession


class CombinableLoader(abc.ABC):
    @abc.abstractmethod
    def __call__(self, shot: Shot, session: ExperimentSession) -> polars.DataFrame:
        ...

    def __add__(self, other):
        if isinstance(other, CombinableLoader):
            return HorizontalConcatenateLoader(self, other)
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
