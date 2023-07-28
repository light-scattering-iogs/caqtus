import logging

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import stft

from aod_tweezer_arranger.runtime import SignalGenerator
from aod_tweezer_arranger.runtime.signal_generator import NumberSamples
from duration_timer import DurationTimerLog

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def test_moving_traps():
    sampling_rate = 625_000_000
    with SignalGenerator(sampling_rate=sampling_rate) as signal_generator:
        initial_frequencies = np.linspace(77e6, 86e6, 15)
        final_frequencies = initial_frequencies - 2e6

        initial_amplitudes = np.ones(len(initial_frequencies)) / len(
            initial_frequencies
        )
        final_amplitudes = initial_amplitudes * 0.5

        initial_phases = np.random.uniform(0, 2 * np.pi, len(initial_frequencies))
        final_phases = initial_phases

        with DurationTimerLog(logger, "Generating signal"):
            output_0 = signal_generator.generate_signal_static_traps(
                initial_amplitudes,
                initial_frequencies,
                initial_phases,
                number_samples=NumberSamples(625_000),
            )
            output_2 = signal_generator.generate_signal_static_traps(
                final_amplitudes,
                final_frequencies,
                final_phases,
                number_samples=NumberSamples(625_000),
            )

            output_1 = signal_generator.generate_signal_moving_traps(
                initial_amplitudes,
                final_amplitudes,
                initial_frequencies,
                final_frequencies,
                initial_phases,
                final_phases,
                number_samples=NumberSamples(625_047),
                previous_step_length=NumberSamples(625_000)
            )

        output = np.concatenate([output_0, output_1, output_2])
        logger.debug(output)
        f, t, Zxx = stft(output, sampling_rate, nperseg=10_000)
        plt.imshow(np.abs(Zxx), aspect="auto", extent=[t.min() * 1e3, t.max() * 1e3, f.min() * 1e-6, f.max() * 1e-6], origin="lower")
        plt.ylim(70, 90)
        plt.xlabel("Time [ms]")
        plt.ylabel("Frequency [MHz]")
        plt.show()
