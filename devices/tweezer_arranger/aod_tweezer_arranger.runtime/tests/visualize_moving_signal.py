import logging
from threading import Thread

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
        final_frequencies = initial_frequencies + 2e6

        initial_amplitudes = np.ones(len(initial_frequencies)) / len(
            initial_frequencies
        )
        final_amplitudes = initial_amplitudes * 0.5

        initial_phases = np.random.uniform(0, 2 * np.pi, len(initial_frequencies))
        final_phases = initial_phases

        with DurationTimerLog(logger, "Generating signal"):
            thread = Thread(target=signal_generator.generate_signal_moving_traps, args=(
                initial_amplitudes,
                final_amplitudes,
                initial_frequencies,
                final_frequencies,
                initial_phases,
                final_phases,
                NumberSamples(625_000),
            ))
            thread.start()
            thread.join()
            output = signal_generator.generate_signal_moving_traps(
                initial_amplitudes,
                final_amplitudes,
                initial_frequencies,
                final_frequencies,
                initial_phases,
                final_phases,
                number_samples=NumberSamples(625_000),
            )
        logger.debug(output)
        f, t, Zxx = stft(output, sampling_rate, nperseg=6_250)
        plt.imshow(np.abs(Zxx), aspect="auto", extent=[t.min(), t.max(), f.min(), f.max()], origin="lower")
        plt.ylim(70e6, 90e6)
        plt.xlabel("Time [sec]")
        plt.ylabel("Frequency [Hz]")
        plt.show()
