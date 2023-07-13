from warnings import warn

import numpy as np

from trap_signal_generator.runtime import StaticTrapGenerator

file_x = "./config_x.yaml"
file_y = "./config_y.yaml"

number_samples = 19539 * 32
sampling_rate = 625_000_000
segment_frequency = sampling_rate / number_samples

# frequencies_x = np.array([82e6])
# frequencies_x = np.linspace(77e6, 86e6, 5)

frequencies_x = np.linspace(80e6, 84e6, 5)

spacing_x = frequencies_x[1] - frequencies_x[0]
spacing_x = np.round(spacing_x / segment_frequency) * segment_frequency
frequencies_x = frequencies_x[0] + np.arange(len(frequencies_x)) * spacing_x

# frequencies_y = np.array([76e6])
# frequencies_y = np.linspace(72e6, 81e6, 5)

frequencies_y = np.linspace(75e6, 79e6, 5)

spacing_y = frequencies_y[1] - frequencies_y[0]
spacing_y = np.round(spacing_y / segment_frequency) * segment_frequency
frequencies_y = frequencies_y[0] + np.arange(len(frequencies_y)) * spacing_y

frequencies_x = np.round(frequencies_x / segment_frequency) * segment_frequency
frequencies_y = np.round(frequencies_y / segment_frequency) * segment_frequency

NX, NY = len(frequencies_x), len(frequencies_y)

amplitudes_x = np.ones(len(frequencies_x)) / NX * (2**15 - 1)
amplitudes_y = np.ones(len(frequencies_y)) / NY * (2**15 - 1)

static_trap_generator_x = StaticTrapGenerator(
    frequencies=frequencies_x,
    amplitudes=amplitudes_x,
    phases=np.random.uniform(0, 2 * np.pi, NX),
    sampling_rate=sampling_rate,
    number_samples=number_samples,
)

if (
    smallest_beating_x := static_trap_generator_x.compute_smallest_frequency_beating(4)
) < 100e3:
    warn(f"There is beating of {smallest_beating_x*1e-3:.1f} kHz in the X channel")

static_trap_generator_x.optimize_phases()
config_x = static_trap_generator_x.get_configuration()
with open(file_x, "w") as f:
    f.write(config_x.to_yaml())

static_trap_generator_y = StaticTrapGenerator(
    frequencies=frequencies_y,
    amplitudes=amplitudes_y,
    phases=np.random.uniform(0, 2 * np.pi, NY),
    sampling_rate=sampling_rate,
    number_samples=number_samples,
)

if (
    smallest_beating_y := static_trap_generator_y.compute_smallest_frequency_beating(4)
) < 100e3:
    warn(f"There is beating of {smallest_beating_y*1e-3:.1f} kHz in the Y channel")

static_trap_generator_x.optimize_phases()
config_y = static_trap_generator_y.get_configuration()
with open(file_y, "w") as f:
    f.write(config_y.to_yaml())
