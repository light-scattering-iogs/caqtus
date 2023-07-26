import math
from typing import NewType, SupportsFloat, SupportsInt

import numpy as np
# This import is required to initialize cuda driver and context.
# See documentation for manual initialization.
# noinspection PyUnresolvedReferences
import pycuda.autoinit
import pycuda.driver as cuda
from pycuda.compiler import SourceModule

from .static_traps_cuda import get_static_traps_cuda_program

NumberTones = NewType("NumberTones", int)
NumberSamples = NewType("NumberSamples", int)

NUMBER_THREADS_PER_BLOCK = 1024

AWGSignalArray = np.ndarray[NumberSamples, np.dtype[np.int16]]


class SignalGenerator:

    def __init__(
            self, sampling_rate: SupportsFloat, max_number_tones: SupportsInt = 200
    ):
        self._sampling_rate = float(sampling_rate)
        self._time_step = 1 / self._sampling_rate
        self._max_number_tones = int(max_number_tones)
        self._setup_cuda()

    @property
    def sampling_rate(self) -> float:
        return self._sampling_rate

    @property
    def time_step(self) -> float:
        return self._time_step

    def _setup_cuda(self):
        source = get_static_traps_cuda_program(self._max_number_tones)
        self._module = SourceModule(source)
        self._compute_static_traps_signal = self._module.get_function(
            "compute_static_traps_signal"
        )
        self._amplitudes_gpu = self._module.get_global("amplitudes")[0]
        self._frequencies_gpu = self._module.get_global("frequencies")[0]
        self._phases_gpu = self._module.get_global("phases")[0]

    def generate_signal_static_traps(
            self,
            amplitudes: np.ndarray[NumberTones, np.dtype[float]],
            frequencies: np.ndarray[NumberTones, np.dtype[float]],
            phases: np.ndarray[NumberTones, np.dtype[float]],
            number_samples: NumberSamples,
    ) -> AWGSignalArray:
        number_tones = len(amplitudes)
        if not len(phases) == len(frequencies) == number_tones:
            raise ValueError(
                "Lengths of amplitudes, phases and frequencies must be equal."
            )

        output = np.zeros(number_samples, dtype=np.int16)
        amplitudes_f32 = np.array(amplitudes, dtype=np.float32)
        frequencies_f32 = np.array(frequencies, dtype=np.float32)
        phases_f32 = np.array(phases, dtype=np.float32)
        cuda.memcpy_htod(self._amplitudes_gpu, amplitudes_f32)
        cuda.memcpy_htod(self._frequencies_gpu, frequencies_f32)
        cuda.memcpy_htod(self._phases_gpu, phases_f32)

        block = (NUMBER_THREADS_PER_BLOCK, 1, 1)
        grid = (math.ceil(number_samples / NUMBER_THREADS_PER_BLOCK), 1, 1)
        self._compute_static_traps_signal(
            cuda.Out(output),
            np.uint32(number_samples),
            np.uint32(number_tones),
            np.float32(self._time_step),
            block=block,
            grid=grid,
        )
        return output
