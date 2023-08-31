import logging

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import stft

from aod_tweezer_arranger.runtime import SignalGenerator
from aod_tweezer_arranger.runtime.signal_generator import NumberSamples
from duration_timer import DurationTimerLog

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


trap_frequencies = (
    68999620.95040688,
    69611378.20512821,
    70223135.45984954,
    70834892.71457085,
    71446649.96929218,
    72058407.2240135,
    72670164.47873484,
    73281921.73345616,
    73893678.9881775,
    74505436.24289882,
    75117193.49762014,
    75728950.75234146,
    76340708.0070628,
    76952465.26178412,
    77564222.51650545,
    78175979.77122678,
    78787737.0259481,
    79399494.28066942,
    80011251.53539075,
    80623008.79011208,
    81234766.0448334,
    81846523.29955474,
    82458280.55427606,
    83070037.8089974,
    83681795.0637187,
    84293552.31844003,
    84905309.57316136,
    85517066.82788269,
    86128824.08260402,
    86740581.33732535,
    87352338.59204668,
    87964095.846768,
    88575853.10148932,
    89187610.35621065,
    89799367.61093198,
    90411124.8656533,
    91022882.12037463,
    91634639.37509596,
    92246396.62981729,
    92858153.8845386,
    93469911.13925993,
    94081668.39398126,
    94693425.64870259,
    95305182.90342392,
    95916940.15814525,
    96528697.41286658,
    97140454.66758789,
    97752211.92230922,
    98363969.17703055,
    98975726.43175188,
)


def test_moving_traps_gpu():
    sampling_rate = 625_000_000
    with SignalGenerator(sampling_rate=sampling_rate) as signal_generator:
        initial_frequencies = np.array(trap_frequencies)
        initial_amplitudes = np.ones(len(initial_frequencies)) / len(
            initial_frequencies
        )
        initial_phases = np.random.uniform(0, 2 * np.pi, len(initial_frequencies))

        final_amplitudes = initial_amplitudes
        final_frequencies = initial_frequencies + 1e6 * 0
        final_phases = initial_phases

        T = 625248

        with DurationTimerLog(logger, "Generating signal"):
            output_0 = signal_generator.generate_signal_static_traps(
                initial_amplitudes,
                initial_frequencies,
                initial_phases,
                number_samples=NumberSamples(T),
            )[:2 * (T//3)]
            output_2 = signal_generator.generate_signal_static_traps(
                final_amplitudes,
                final_frequencies,
                final_phases,
                number_samples=NumberSamples(T),
            )[1 * (T//3):]

            output_1 = signal_generator.generate_signal_moving_traps(
                initial_amplitudes,
                final_amplitudes,
                initial_frequencies,
                final_frequencies,
                initial_phases,
                final_phases,
                number_samples=NumberSamples(2 * (T//3)),
                previous_step_stop=2 * (T//3),
                next_step_start=(4 * (T//3)) % T
            )

        output = np.concatenate([output_0, output_1, output_2])
        logger.debug(output)
        f, t, Zxx = stft(output, sampling_rate, nperseg=5_000)
        plt.imshow(
            np.abs(Zxx),
            aspect="auto",
            extent=[t.min() * 1e3, t.max() * 1e3, f.min() * 1e-6, f.max() * 1e-6],
            origin="lower",
        )
        plt.ylim(60, 110)
        plt.xlabel("Time [ms]")
        plt.ylabel("Frequency [MHz]")
        # plt.axvline(T // 2 / sampling_rate * 1e3, color="white", ls="--", alpha=0.5)
        # plt.axvline(3 * T // 2 / sampling_rate * 1e3, color="white", ls="--", alpha=0.5)
        plt.show()
