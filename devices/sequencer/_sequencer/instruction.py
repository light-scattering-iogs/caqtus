from abc import ABC
from typing import TypeVar, Generic, Iterable, Self

import numpy as np

from sequencer.splittable import Splittable

PatternType = TypeVar("PatternType", bound=Splittable, covariant=True)

SubInstruction = TypeVar("SubInstruction", bound="Instruction", covariant=True)

#
# class Instruction(Splittable[SubInstruction], Generic[PatternType, SubInstruction], ABC):
#     """Base class to describe high-level instructions.
#
#     An instruction is generic on the type of pattern it contains, and the type of instruction it returns when split. All
#     classes inheriting from this class must be effectively immutable. More precisely, its length must not change.
#     """
#
#     pass
#
#
# class Concatenate(
#     Instruction[PatternType, SubInstruction]
# ):
#     """A sequence of instructions to be executed consecutively.
#
#     Attributes:
#         instructions: The instructions to be executed
#     """
#
#     def __init__(
#         self,
#         instructions: Iterable[SubInstruction | PatternType],
#     ) -> None:
#         self._instructions = tuple(instructions)
#         self._instruction_starts = np.cumsum(
#             [0] + [len(instruction) for instruction in instructions]
#         )
#         self._check_length_valid()
#
#     @property
#     def instructions(self) -> tuple[SubInstruction | PatternType, ...]:
#         return self._instructions
#
#     def __len__(self) -> int:
#         return sum(len(instruction) for instruction in self.instructions)
#
#     def split(self, split_index: int) -> tuple[Self, Self]:
#         self._check_split_valid(split_index)
#
#         instruction_index = self._find_instruction_index(split_index)
#         instruction_to_split = self.instructions[instruction_index]
#
#         if split_index == self._instruction_starts[instruction_index]:
#             a = []
#             b = [instruction_to_split]
#         elif split_index == self._instruction_starts[instruction_index] + len(
#             instruction_to_split
#         ):
#             a = [instruction_to_split]
#             b = []
#         else:
#             x, y = instruction_to_split.split(
#                 split_index - self._instruction_starts[instruction_index]
#             )
#             a, b = [x], [y]
#         cls = type(self)
#         first_part = cls(list(self.instructions[:instruction_index]) + a)
#         second_part = cls(b + list(self.instructions[instruction_index + 1 :]))
#         return first_part, second_part
#
#     def _find_instruction_index(self, time: int) -> int:
#         """Find the index of the instruction active at the given time index."""
#
#         if time < 0:
#             raise ValueError(f"Time index must be non-negative, got {time}.")
#         if time >= len(self):
#             raise ValueError(f"Time index must be less than {len(self)}, got {time}.")
#
#         return int(np.searchsorted(self._instruction_starts, time, side="right") - 1)
#
#     def __repr__(self) -> str:
#         return f"{self.__class__.__name__}({self.instructions!r})"
#
#     def __str__(self) -> str:
#         return f"{self.__class__.__name__}({self.instructions!s})"


