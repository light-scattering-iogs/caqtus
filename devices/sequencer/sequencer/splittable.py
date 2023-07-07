from abc import abstractmethod
from typing import Protocol, Sized, TypeVar

SplitResult = TypeVar("SplitResult", bound="Splittable", covariant=True)


class Splittable(Sized, Protocol[SplitResult]):
    def _check_length_valid(self) -> None:
        if len(self) < 0:
            raise ValueError(f"Sequence can't have negative length.")
        elif len(self) == 0:
            raise ValueError("Empty sequence is not splittable.")

    @abstractmethod
    def split(self, split_index: int) -> tuple[SplitResult, SplitResult]:
        """Split the instruction into two parts at the given index.

        Args:
            split_index: The index at which to split the instruction. Must be 0 < split_index < len(self).

        Returns:
            A tuple containing the two parts of the instruction. The first part contains the values with indices
            0 <= i < split_index, the second part contains the values with indices split_index <= i < len(self).
        """

        raise NotImplementedError

    def _check_split_valid(self, split_index: int) -> None:
        """Check whether the given split index is valid."""

        if not (0 < split_index < len(self)):
            raise ValueError(
                f"Invalid split index {split_index} for instruction of length"
                f" {len(self)}."
            )
