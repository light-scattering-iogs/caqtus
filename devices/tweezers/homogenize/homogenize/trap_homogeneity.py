import logging
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from awg import initialize_awg
from monitor_trap_intensities import TrapIntensitiesMeasurer
from trap_signal_generator.configuration import StaticTrapConfiguration
from trap_signal_generator.runtime import StaticTrapGenerator

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")
logging.basicConfig()

@dataclass
class HomogenizeTraps:
    n_iter: int
    exposure: int
    flip_horizontal: bool
    nx: int
    ny: int
    amplitudes_x: Sequence[float]
    amplitudes_y: Sequence[float]
    fx: Sequence[float]
    fy: Sequence[float]
    phi_x: list[float]
    phi_y: list[float]
    awg_amplitude_x: int
    awg_amplitude_y: int
    config_x: StaticTrapConfiguration
    config_y: StaticTrapConfiguration

    trap_intensity_measure: TrapIntensitiesMeasurer = field(init=False)

    threshold: float = 0.3
    beta: float = 0.5
    n_bits: int = 12

    def __post_init__(self):
        self.trap_intensity_measure = TrapIntensitiesMeasurer(
            number_columns=self.nx,
            number_rows=self.ny,
            flip_horizontal=self.flip_horizontal,
            exposure=self.exposure,
            threshold=self.threshold,
        )

    def image_traps(self, a_x, a_y, n_bits):
        AWG = initialize_awg(self.config_x, self.config_y)
        with AWG as awg_device:
            self.config_x.amplitudes = a_x
            self.config_y.amplitudes = a_y
            static_trap_generator_x = StaticTrapGenerator.from_configuration(self.config_x)
            static_trap_generator_y = StaticTrapGenerator.from_configuration(self.config_y)
            data_0 = np.int16(
                (
                    static_trap_generator_x.compute_signal(),
                    static_trap_generator_y.compute_signal(),
                )
            )
            static_trap_generator_y.frequencies = (
                    np.array(static_trap_generator_y.frequencies) + 4e6
            )
            data_1 = np.int16(
                (
                    static_trap_generator_x.compute_signal(),
                    static_trap_generator_y.compute_signal(),
                )
            )

            awg_device.write_segment_data("segment_0", data_0)
            awg_device.write_segment_data("segment_1", data_1)
            awg_device.run()
            image = self.trap_intensity_measure.take_photo(n_bits)
            awg_device.stop()
            return image

    def homogenize(self):
        new_amp_x, new_amp_y = self.amplitudes_x, self.amplitudes_y
        gain_x, gain_y = np.ones(self.nx), np.ones(self.ny)
        # background = self.trap_intensity_measure.take_photo(self.n_bits)
        image_before = self.image_traps(new_amp_x, new_amp_y, self.n_bits).T[::-1]
        matrix_of_sorted_intensities_before = self.trap_intensity_measure.sort_traps(image_before, self.ny, self.nx)
        std_dev = np.zeros([self.n_iter, 3])

        for i in range(self.n_iter):
            print('iteration number :', i)
            new_amp_x, new_amp_y = gain_x * new_amp_x, gain_y * new_amp_y
            image = self.image_traps(new_amp_x, new_amp_y, self.n_bits).T[::-1]
            matrix_of_sorted_intensities = self.trap_intensity_measure.sort_traps(image, self.ny, self.nx)
            new_gain = find_new_amplitudes(matrix_of_sorted_intensities, self.ny, self.nx, new_amp_x, new_amp_y, self.beta)
            gain_x, gain_y = new_gain[0], new_gain[1]
            intensity_x, intensity_y = new_gain[2], new_gain[3]
            std_dev[i][0] = np.sqrt(np.var(intensity_x)) / np.mean(intensity_x)
            std_dev[i][1] = np.sqrt(np.var(intensity_y)) / np.mean(intensity_y)
            std_dev[i][2] = np.sqrt(np.var(matrix_of_sorted_intensities[:, :, 2])) / np.mean(
                matrix_of_sorted_intensities[:, :, 2])
            if i > 0:
                verify_convergence(std_dev[i - 1, :], std_dev[i, :])
        image_after = self.image_traps(new_amp_x, new_amp_y, self.n_bits).T[::-1]
        matrix_of_sorted_intensities_after = self.trap_intensity_measure.sort_traps(image_after, self.ny, self.nx)
        return new_amp_x, new_amp_y, image_before, image_after, matrix_of_sorted_intensities_before, matrix_of_sorted_intensities_after, std_dev


# Input list of sorted intensities :
def find_new_amplitudes(intensities_matrix, number_rows: int, number_columns: int, a_x, a_y, beta):
    intensities_x, intensities_y = np.zeros(number_columns), np.zeros(number_rows)
    for i in range(0, number_columns):
        intensities_x[i] = np.mean(intensities_matrix[:, i][:, -1])
    for j in range(0, number_rows):
        intensities_y[j] = np.mean(intensities_matrix[j, :][:, -1])
    alpha_x = intensities_x / np.sum(intensities_x)
    # alpha_y = intensities_y[::-1] / np.sum(intensities_y)
    alpha_y = intensities_y / np.sum(intensities_y)
    gain_y = (1 / alpha_y ** beta) * number_rows / np.sum(a_y / alpha_y ** beta)
    gain_x = (1 / alpha_x ** beta) * number_columns / np.sum(a_x / alpha_x ** beta)
    return gain_x, gain_y, intensities_x, intensities_y

def verify_convergence(std_dev_prev, std_dev_current):
    if std_dev_current[0] > std_dev_prev[0] or std_dev_current[1] > std_dev_prev[1] or std_dev_current[2] > \
            std_dev_prev[2]:
        print('CONVERGENCE PROBLEM - HOMOGENIZATION IS NOT WORKING')
