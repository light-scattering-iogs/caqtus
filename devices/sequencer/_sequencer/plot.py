import numpy as np
from matplotlib.axes import Axes

from .time_sequence import TimeSequence


def plot_channel(time_sequence: TimeSequence, channel_index: int, ax: Axes, **kwargs):
    pattern = time_sequence.unroll()

    times = [0.] + list(np.cumsum(pattern.durations) * time_sequence.time_step)
    channel_values = list(pattern.channel_values[channel_index]) + [time_sequence.channel_configs[channel_index].final_value]

    ax.plot(times, channel_values, drawstyle="steps-post", **kwargs)