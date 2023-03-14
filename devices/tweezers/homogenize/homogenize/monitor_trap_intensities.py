from contextlib import closing
from dataclasses import dataclass

import cv2
import numpy as np

from pixelfly import PixelflyBoard, Mode, BinMode, PixelDepth


@dataclass
class TrapIntensitiesMeasurer:
    number_columns: int
    number_rows: int
    flip_horizontal: bool
    exposure: int = 500
    threshold: float = 0.3

    def take_photo(self, n_bits: int):
        with closing(PixelflyBoard(board_number=0)) as board:
            if n_bits == 8:
                board.set_mode(mode=Mode.SW_TRIGGER | Mode.ASYNC_SHUTTER, exp_time=self.exposure, hbin=BinMode.BIN_1X,
                               vbin=BinMode.BIN_1X, gain=False, bit_pix=PixelDepth.BITS_8)
            elif n_bits == 12:
                board.set_mode(mode=Mode.SW_TRIGGER | Mode.ASYNC_SHUTTER, exp_time=self.exposure, hbin=BinMode.BIN_1X,
                               vbin=BinMode.BIN_1X, gain=False, bit_pix=PixelDepth.BITS_12)
            else:
                print('Wrong number of bits, taking 8 bits')
                board.set_mode(mode=Mode.SW_TRIGGER | Mode.ASYNC_SHUTTER, exp_time=self.exposure, hbin=BinMode.BIN_1X,
                               vbin=BinMode.BIN_1X, gain=False, bit_pix=PixelDepth.BITS_8)
            board.start_camera()
            if self.flip_horizontal:
                im = board.read_image(1000)[::, ::-1]
            else:
                im = board.read_image(1000)
            board.stop_camera()
        im = im.astype(float)
        return im

    def _find_traps(self, image):
        max_intensity = np.max(image)
        img_thr = np.uint8((image > np.ones_like(image) * max_intensity * self.threshold) * 1)
        num_labels, labels, stats, barycenters = cv2.connectedComponentsWithStats(img_thr)
        # Find background label:
        background_label = np.where(np.bincount(labels.flatten()) == max(np.bincount(labels.flatten())))[0]
        print('Number of traps: ', num_labels - 1)
        return num_labels, labels, stats, barycenters, background_label

    def measure_intensities(self, image):
        num_labels, labels, stats, barycenters, background_label = self._find_traps(image)
        intensities_and_barycenter = np.zeros([num_labels, 3])
        mask = np.ones_like(image) * 500
        min_ = np.min(image)
        horizontal_size, vertical_size = np.sort(stats[:, 2])[-2], np.sort(stats[:, 3])[-2]
        for i in range(0, num_labels):
            if i != background_label:
                intensities_and_barycenter[i, 0] = barycenters[i, 0]
                intensities_and_barycenter[i, 1] = barycenters[i, 1]
                y, x = int(barycenters[i, 0] - horizontal_size), int(barycenters[i, 1] - vertical_size)
                px = image[x:int(x + 2 * horizontal_size + 5), y:int(y + 2 * vertical_size + 5)]
                mask[x:int(x + 2 * horizontal_size + 5), y:int(y + 2 * vertical_size + 5)] = image[x:int(
                    x + 2 * horizontal_size + 5), y:int(y + 2 * vertical_size + 5)]
                intensity_square = np.sum(px - min_)
                intensity_square = intensity_square / (horizontal_size * vertical_size)
                intensities_and_barycenter[i, 2] = intensity_square
        intensities_and_barycenter = intensities_and_barycenter[~np.all(intensities_and_barycenter == 0, axis=1)]
        return intensities_and_barycenter, mask

    def sort_traps(self, image, number_rows: int, number_columns: int):
        intensities_and_barycenter = self.measure_intensities(image)[0]
        for i in range(0, number_rows):
            b = intensities_and_barycenter[i * number_columns: (i+1) * number_columns]
            intensities_and_barycenter[i * number_columns: (i+1) * number_columns] = b[b[:, 0].argsort()]
        matrix_intensities = np.reshape(intensities_and_barycenter, (number_rows, number_columns, 3))
        return matrix_intensities