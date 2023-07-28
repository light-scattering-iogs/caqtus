import numpy as np


def amplitude_ramp(s):
    return -1.0 + 2.0 * s


def phase_ramp(s):
    return -np.sin(np.pi * s) / np.pi


def compute_moving_traps_signal(
    initial_amplitudes,
    final_amplitudes,
    initial_frequencies,
    final_frequencies,
    initial_phases,
    final_phases,
    number_samples,
    previous_step_length,
    time_step,
):
    output = np.zeros(number_samples, dtype=np.int16)
    for tid in range(number_samples):
        s = tid / number_samples
        result = 0.0
        T = time_step * number_samples

        number_tones = len(initial_amplitudes)

        for i in range(number_tones):
            mean_frequency = 0.5 * (initial_frequencies[i] + final_frequencies[i])
            frequency_range = 0.5 * (final_frequencies[i] - initial_frequencies[i])
            initial_phase = (
                initial_phases[i]
                + 2 * np.pi * previous_step_length * time_step * initial_frequencies[i]
            )
            phase_mismatch = (
                final_phases[i] - initial_phase - (2 * np.pi * T) * mean_frequency
            )
            if frequency_range == 0.0:
                s0 = 1.0
            else:
                phase_remainder = phase_mismatch
                s0 = 1.0 - phase_remainder / (2 * np.pi * T * frequency_range)
            if s < s0:
                phase = initial_phase + 2 * np.pi * T * (
                    s * mean_frequency + frequency_range * s0 * phase_ramp(s / s0)
                )
            else:
                phase = initial_phase + 2 * np.pi * T * (
                    s * mean_frequency + frequency_range * (s - s0)
                )
            mean_amplitude = 0.5 * (initial_amplitudes[i] + final_amplitudes[i])
            amplitude_range = 0.5 * (final_amplitudes[i] - initial_amplitudes[i])
            amplitude = mean_amplitude + amplitude_range * amplitude_ramp(s)
            result += amplitude * np.sin(phase)
        output[tid] = np.int16(result * 32767.999)
    return output
