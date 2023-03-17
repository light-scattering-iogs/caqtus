import matplotlib.pyplot as plt
import numpy as np

from awg import initialize_awg
from monitor_trap_intensities import TrapIntensitiesMeasurer
from trap_homogeneity import HomogenizeTraps
from trap_signal_generator.configuration import StaticTrapConfiguration

flip_horizontal = False
number_iterations = 5
exposure_time = 50
threshold = 0.21
beta_power = 0.5


with open("../tweezers.utilities.run_awg/config_x.yaml", "r") as f:
    config_x = StaticTrapConfiguration.from_yaml(f.read())

with open("../tweezers.utilities.run_awg/config_y.yaml", "r") as f:
    config_y = StaticTrapConfiguration.from_yaml(f.read())

frequencies_x = config_x.frequencies
frequencies_y = config_y.frequencies
n_tones_x = config_x.number_tones
n_tones_y = config_y.number_tones
amplitudes_x = config_x.amplitudes
amplitudes_y = config_y.amplitudes
phase_x = config_x.phases
phase_y = config_y.phases
amplitude_one_tone = 0.135
awg_amplitude_x = int(np.sqrt(n_tones_x) * amplitude_one_tone)
awg_amplitude_y = int(np.sqrt(n_tones_y) * amplitude_one_tone)


awg_device = initialize_awg(config_x, config_y)


def run_homogenization():
    trap_intensity_measure: TrapIntensitiesMeasurer(
        number_columns=n_tones_x,
        number_rows=n_tones_y,
        flip_horizontal=flip_horizontal,
        exposure=exposure_time,
        threshold=threshold,
    )

    homogenizer = HomogenizeTraps(
        n_iter=number_iterations,
        exposure=exposure_time,
        flip_horizontal=False,
        nx=n_tones_x,
        ny=n_tones_y,
        fx=frequencies_x,
        fy=frequencies_y,
        amplitudes_x=amplitudes_x,
        amplitudes_y=amplitudes_y,
        phi_x=phase_x,
        phi_y=phase_y,
        awg_amplitude_x=awg_amplitude_x,
        awg_amplitude_y=awg_amplitude_y,
        threshold=threshold,
        beta=beta_power,
        config_x=config_x,
        config_y=config_y
    )
    # image_before = homogenizer.image_traps(amplitudes_x, amplitudes_y, 12)
    new_amp_x, new_amp_y, image_before, image_after, matrix_of_sorted_intensities_before, matrix_of_sorted_intensities_after, std_dev = homogenizer.homogenize()
    intensities_before = np.reshape(matrix_of_sorted_intensities_before[:, :, -1], (1, n_tones_x*n_tones_y))[0]
    intensities_after = np.reshape(matrix_of_sorted_intensities_after[:, :, -1], (1, n_tones_x*n_tones_y))[0]
    print("New x amplitude =", new_amp_x)
    print("New y amplitude =", new_amp_y)

    plt.figure(1)
    plt.imshow(image_before)
    plt.title('Before homog')
    plt.show()

    plt.figure(2)
    plt.imshow(image_after)
    plt.title('After homog')
    plt.show()

    plt.figure(3)
    plt.hist(intensities_before, label="before homog")
    plt.hist(intensities_after, label="after 10 iterations of homog")
    plt.xlabel("intensity of trap")
    plt.ylabel("number of traps")
    plt.legend()
    plt.show()

    plt.figure(4)
    plt.plot(std_dev[:, 0], label='vertical')
    plt.plot(std_dev[:, 1], label='horizontal')
    plt.plot(std_dev[:, 2], label='all traps')
    plt.xlabel('iteration')
    plt.ylabel('std/mean')
    plt.legend()
    plt.show()

run_homogenization()