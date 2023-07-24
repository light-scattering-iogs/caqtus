import time

import matplotlib.pyplot as plt
import numpy as np

from signal_generator import SignalGenerator

MAX_NUMBER_TONES = 1000


def compute_signal(times, amplitudes, frequencies, phases):
    return sum(
        amplitude * np.sin(2 * np.pi * times * frequency + phase)
        for amplitude, frequency, phase in zip(amplitudes, frequencies, phases)
    )


def main():
    sg = SignalGenerator(sampling_rate=625_000_000)

    number_tones = 100
    frequencies = np.linspace(77e6, 86e6, number_tones)
    phases = np.random.uniform(0, 2 * np.pi, number_tones)
    amplitudes = np.linspace(0.8, 1, number_tones) / number_tones

    number_samples = 625_000

    times = np.arange(number_samples) * sg.time_step

    t0 = time.perf_counter()
    output = sg.generate_signal_static_traps(
        amplitudes, frequencies, phases, number_samples
    )
    t1 = time.perf_counter()
    print(f"{(t1 - t0) * 1e3} ms")

    plt.plot(output)
    t0 = time.perf_counter()
    y = compute_signal(times, amplitudes, frequencies, phases)
    t1 = time.perf_counter()
    plt.plot(y * 2 ** 15, ls="--")
    print(f"{(t1 - t0) * 1e3} ms")

    # plt.plot(y - output)

    plt.xlim(500_000, 500_000 + 150)
    plt.show()
    print(output[-1])


if __name__ == "__main__":
    main()
