import numpy as np
from matplotlib.axes import Axes

from .time_sequence import TimeSequence


def plot_channel(time_sequence: TimeSequence, channel_index: int, ax: Axes, **kwargs):
    pattern = time_sequence.unroll()
    times = np.cumsum(pattern.durations) * time_sequence.time_step
    channel_values = pattern.channel_values[channel_index]

    ax.plot(times, channel_values, drawstyle="steps-post", **kwargs)