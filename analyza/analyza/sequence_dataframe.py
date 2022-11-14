from abc import ABC, abstractmethod
from itertools import chain, tee
from pathlib import Path
from typing import Any
from typing import Optional, Literal

import pandas
import pint_pandas
from tqdm.notebook import tqdm

from sequence.sequence import Sequence, Shot
from units import ureg, Quantity

pint_pandas.PintType.ureg = ureg
pint_pandas.PintType.ureg.default_format = "P~"

tqdm.pandas()


class SequenceDataframe(pandas.DataFrame, ABC):
    def __init__(
        self,
        sequence_names: str | list[str],
        units: Optional[Literal["strip"] | Literal["column"]] = None,
    ):
        if isinstance(sequence_names, str):
            sequence_names = [sequence_names]
        sequences = [Sequence(Path(sequence_name)) for sequence_name in sequence_names]

        s1, s2 = tee(chain(*sequences))
        indices = [(shot.sequence.relative_path, shot.name) for shot in s1]
        index = pandas.MultiIndex.from_tuples(indices, names=["sequence", "shot"])
        total = sum(len(sequence) for sequence in sequences)
        rows = tqdm(map(self.convert_shot_to_row, s2), total=total)
        super().__init__(rows, index=index)

        if units is not None:
            for name, value in self.iloc[0].items():
                if isinstance(value, Quantity):
                    units_ = value.units
                    dtype = None
                    if units == "column":
                        if str(units_) != "":
                            dtype = f"pint[{units_}]"
                    self[name] = pandas.Series(
                        self[name].apply(lambda x: x.to(units_).magnitude),
                        dtype=dtype,
                    )

    @abstractmethod
    def convert_shot_to_row(self, shot: Shot) -> dict[str, Any]:
        ...
