import matplotlib.pyplot as plt

from sequencer.channel_config import ChannelConfig
from sequencer.plot import plot_channel
from sequencer.time_sequence import TimeSequence


def main():
    channel_configs = [
        ChannelConfig[bool](
            default_value=False, initial_value=False, final_value=False
        ),
    ]

    sequence = TimeSequence(time_step=1, channel_configs=channel_configs)

    pattern = sequence.append_new_pattern([1, 2, 3])
    pattern.set_values(0, [True, False, True])

    pattern_2 = sequence.append_new_pattern([4, 5, 6])
    pattern_2.set_values(0, [False, True, False])

    plot_channel(sequence, 0, plt.gca())
    plt.show()


if __name__ == "__main__":
    main()
