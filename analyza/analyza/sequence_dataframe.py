from typing import Any, Callable

import pandas
from tqdm.notebook import tqdm

from experiment.session import ExperimentSession
from sequence.runtime import Sequence, Shot


# pint_pandas.PintType.ureg = ureg
# pint_pandas.PintType.ureg.default_format = "P~"
#
# tqdm.pandas()


def build_dataframe_from_sequence(
    sequence: Sequence,
    shot_to_row_converter: Callable[[Shot, ExperimentSession], dict[str, Any]],
    session: ExperimentSession,
):
    with session:
        shots = sequence.get_shots(session)

    def map_shot_to_row(shot):
        with session:
            return shot_to_row_converter(shot, session)

    indices = [(str(shot.sequence.path), shot.index) for shot in shots]
    index = pandas.MultiIndex.from_tuples(indices, names=["sequence", "shot"])
    rows = list(tqdm(map(map_shot_to_row, shots), total=len(shots)))
    return pandas.DataFrame(rows, index=index)


# class _SequenceDataframe(pandas.DataFrame, ABC):
#     def __init__(
#         self,
#         /,
#         *sequence_names,
#         root: Path = Path("D:data"),
#         units: Optional[Literal["strip"] | Literal["column"]] = None,
#     ):
#         sequences = [Sequence(Path(sequence_name)) for sequence_name in sequence_names]
#
#         s1, s2 = tee(chain(*sequences))
#         indices = [(shot.sequence.path.relative_to(root), shot.name) for shot in s1]
#         index = pandas.MultiIndex.from_tuples(indices, names=["sequence", "shot"])
#         total = sum(len(sequence) for sequence in sequences)
#         rows = tqdm(map(self.convert_shot_to_row, s2), total=total)
#         super().__init__(rows, index=index)
#         with warnings.catch_warnings():
#             self._units = {}
#
#         for name, value in self.iloc[0].items():
#             if isinstance(value, Quantity):
#                 units_ = value.units
#                 self._units[name] = units_
#                 dtype = None
#                 if units is not None:
#                     if units == "column":
#                         if str(units_) != "":
#                             dtype = f"pint[{units_}]"
#                     self[name] = pandas.Series(
#                         self[name].apply(lambda x: x.to(units_).magnitude),
#                         dtype=dtype,
#                     )
#
#     @abstractmethod
#     def convert_shot_to_row(self, shot: Shot) -> dict[str, Any]:
#         ...
#
#     @property
#     def units(self):
#         return copy.copy(self._units)
