from typing import Protocol

from ._subsequence import SubSequence


class ScoreFunction(Protocol):
    """Protocol for a score function used in Bayesian optimization.

    Example:
        If we want to maximize the atom number of an experiment that outputs the number
        of atoms, with a subsequence that look like this:
        ```
        ┌─────────────┬────────────┬─────────────┐
        │ sequence    ┆ shot_index ┆ atom_number │
        │ ---         ┆ ---        ┆ ---         │
        │ cat         ┆ u64        ┆ u64         │
        ╞═════════════╪════════════╪═════════════╡
        │ my_sequence ┆ 4          ┆ 10          │
        │ my_sequence ┆ 5          ┆ 13          │
        │ my_sequence ┆ 6          ┆ 8           │
        └─────────────┴────────────┴─────────────┘
        ```
        then we can define a score function like this:
        ```python

        def atom_number(subsequence: SubSequence) -> float:
            return subsequence.scan().select(pl.mean("atom_number")).collect().item()
        ```
    """

    def __call__(self, subsequence: SubSequence) -> float:
        """
        Evaluate the score of a given subsequence.

        Returns:
            float: The score of the subsequence.
        """
        ...
