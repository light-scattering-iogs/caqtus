from typing import Optional, TYPE_CHECKING

from ._instructions import TimedInstruction
from ._to_time_array import convert_to_change_arrays

if TYPE_CHECKING:
    from matplotlib.axes import Axes


def plot_instruction(
    instruction: TimedInstruction, ax: Optional["Axes"] = None
) -> "Axes":
    """Plot the instruction on the given axis."""

    import matplotlib.pyplot as plt

    if ax is None:
        fig, ax = plt.subplots()

    change_times, change_values = convert_to_change_arrays(instruction)

    ax.step(change_times, change_values, where="post")
    ax.set_xlabel("Time [ticks]")
    ax.set_ylabel("Value")
    return ax
