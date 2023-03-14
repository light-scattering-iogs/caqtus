import logging
from contextlib import closing
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np
from awg import AWG

from monitor_trap_intensities import TrapIntensitiesMeasurer

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
        with closing(AWG()) as awg_device:
            awg_device.ConnectCard()
            awg_device.setupAWG(self.awg_amplitude_x, self.awg_amplitude_y)

            data = awg_device.write_data_xy(self.fx, self.phi_x, a_x,
                                            self.fy, self.phi_y, a_y)

            awg_device.writeSegmentData(0, len(data) // 2, data, 0)
            awg_device.setFirstSegment(0)
            awg_device.start_output()
            image = self.trap_intensity_measure.take_photo(n_bits)
            awg_device.stop_output()
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
