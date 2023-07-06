import matplotlib.pyplot as plt

from sequencer.channel_config import ChannelConfig
from sequencer.plot import plot_channel
from sequencer.time_sequence import TimeSequence
from sequencer.time_sequence_instructions import Pattern, Repeat


def main():
    channel_configs = [
        ChannelConfig[bool](
            default_value=False, initial_value=False, final_value=False
        ),
    ]

    sequence = TimeSequence(channel_configs=channel_configs)

    pattern = Pattern.create_default_pattern([10, 10, 20], channel_configs)
    pattern.set_values(0, [False, True, False])
    sequence.append(pattern)

    blink = Pattern.create_default_pattern([1, 1], channel_configs)
    blink.set_values(0, [True, False])

    repeat = Repeat([blink], 30)
    sequence.append(repeat)

    plot_channel(sequence, 0, plt.gca(), ls="-", marker=None, color="k")
    plt.show()


if __name__ == "__main__":
    main()
