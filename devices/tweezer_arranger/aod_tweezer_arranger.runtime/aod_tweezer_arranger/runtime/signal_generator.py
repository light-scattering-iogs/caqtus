import logging
import math
import threading
from collections.abc import Sequence
from contextlib import ExitStack
from typing import (
    NewType,
    SupportsFloat,
    SupportsInt,
    Self,
)

import numpy as np
from cuda import nvrtc, cuda, cudart

from .trap_signal_cuda import get_traps_cuda_program
from .with_lock import with_lock

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

NumberTones = NewType("NumberTones", int)
NumberSamples = NewType("NumberSamples", int)

NUMBER_THREADS_PER_BLOCK = 1024

AWGSignalArray = np.ndarray[NumberSamples, np.dtype[np.int16]]


def _check_cuda_error(fun):
    def wrapper(*args, **kwargs):
        err, *result = fun(*args, **kwargs)
        if isinstance(err, cuda.CUresult):
            if err != cuda.CUresult.CUDA_SUCCESS:
                raise CudaError(err)
        elif isinstance(err, cudart.cudaError_t):
            if err != cudart.cudaError_t.cudaSuccess:
                raise CudaError(err)
        elif isinstance(err, nvrtc.nvrtcResult):
            if err != nvrtc.nvrtcResult.NVRTC_SUCCESS:
                raise NvrtcError(err)
        else:
            raise RuntimeError("Unknown error type: {}".format(err))
        if len(result) == 0:
            return None
        elif len(result) == 1:
            return result[0]
        else:
            return result

    return wrapper


nvrtcCreateProgram = _check_cuda_error(nvrtc.nvrtcCreateProgram)
nvrtcCompileProgram = _check_cuda_error(nvrtc.nvrtcCompileProgram)
nvrtcGetPTXSize = _check_cuda_error(nvrtc.nvrtcGetPTXSize)
nvrtcGetPTX = _check_cuda_error(nvrtc.nvrtcGetPTX)
cuInit = _check_cuda_error(cuda.cuInit)
cuDeviceGet = _check_cuda_error(cuda.cuDeviceGet)
cuCtxCreate = _check_cuda_error(cuda.cuCtxCreate)
cuCtxDestroy = _check_cuda_error(cuda.cuCtxDestroy)
cuModuleLoadData = _check_cuda_error(cuda.cuModuleLoadData)
cuModuleUnload = _check_cuda_error(cuda.cuModuleUnload)
cuModuleGetFunction = _check_cuda_error(cuda.cuModuleGetFunction)
cuModuleGetGlobal = _check_cuda_error(cuda.cuModuleGetGlobal)
cuStreamCreate = _check_cuda_error(cuda.cuStreamCreate)
cuStreamDestroy = _check_cuda_error(cuda.cuStreamDestroy)
cuMemAlloc = _check_cuda_error(cuda.cuMemAlloc)
cuMemFree = _check_cuda_error(cuda.cuMemFree)
cuMemcpyHtoDAsync = _check_cuda_error(cuda.cuMemcpyHtoDAsync)
cuLaunchKernel = _check_cuda_error(cuda.cuLaunchKernel)
cuStreamSynchronize = _check_cuda_error(cuda.cuStreamSynchronize)
cuMemcpyDtoHAsync = _check_cuda_error(cuda.cuMemcpyDtoHAsync)
nvrtcGetProgramLogSize = _check_cuda_error(nvrtc.nvrtcGetProgramLogSize)
nvrtcGetProgramLog = _check_cuda_error(nvrtc.nvrtcGetProgramLog)
cuCtxGetCurrent = _check_cuda_error(cuda.cuCtxGetCurrent)
cuCtxSetCurrent = _check_cuda_error(cuda.cuCtxSetCurrent)
cudaSetDevice = _check_cuda_error(cudart.cudaSetDevice)


class SignalGenerator:
    def __init__(
        self, sampling_rate: SupportsFloat, max_number_tones: SupportsInt = 200
    ):
        """Instantiate a new cuda signal generator.

        This object should always be used as a context manager to acquire and release cuda resources properly.
        It is thread safe in the sense that calling methods exploiting the cuda resources are protected by a lock.
        """

        self._sampling_rate = float(sampling_rate)
        self._time_step = 1 / self._sampling_rate
        self._max_number_tones = int(max_number_tones)
        self._exit_stack = ExitStack()
        self.lock = threading.Lock()

    def __enter__(self) -> Self:
        self._exit_stack = ExitStack()
        self._exit_stack.__enter__()
        self._initialize()
        return self

    @with_lock
    def _initialize(self):
        source = get_traps_cuda_program(self._max_number_tones)
        program = nvrtcCreateProgram(
            str.encode(source), b"generate_signal.cu", 0, [], []
        )
        # compute_61 refer to the architecture of the GPU used (6.1)
        # should be replaced for other GPUs
        opts = [b"--fmad=false", b"--gpu-architecture=compute_61"]
        try:
            nvrtcCompileProgram(program, 2, opts)
        except NvrtcError as error:
            log_size = nvrtcGetProgramLogSize(program)
            log = b" " * log_size
            nvrtcGetProgramLog(program, log)
            raise error from NvrtcError(f"{log.decode('utf8')}")
        ptx_size = nvrtcGetPTXSize(program)
        ptx = b" " * ptx_size
        nvrtcGetPTX(program, ptx)
        cuda.cuInit(0)

        # Retrieve handle for device 0, should be changed with multiple GPUs
        cu_device = cuDeviceGet(0)

        self._context = cuCtxCreate(0, cu_device)
        self._exit_stack.callback(cuCtxDestroy, self._context)
        ptx = np.char.array(ptx)
        module = cuModuleLoadData(ptx.ctypes.data)
        self._exit_stack.callback(cuModuleUnload, module)
        self._compute_static_traps_signal = cuModuleGetFunction(
            module, b"compute_static_traps_signal"
        )
        self._compute_moving_traps_signal = cuModuleGetFunction(
            module, b"compute_moving_traps_signal"
        )
        self._amplitudes_gpu = cuModuleGetGlobal(module, b"amplitudes")[0]
        self._frequencies_gpu = cuModuleGetGlobal(module, b"frequencies")[0]
        self._phases_gpu = cuModuleGetGlobal(module, b"phases")[0]
        self._initial_amplitudes_gpu = cuModuleGetGlobal(module, b"initial_amplitudes")[
            0
        ]
        self._initial_frequencies_gpu = cuModuleGetGlobal(
            module, b"initial_frequencies"
        )[0]
        self._initial_phases_gpu = cuModuleGetGlobal(module, b"initial_phases")[0]
        self._final_amplitudes_gpu = cuModuleGetGlobal(module, b"final_amplitudes")[0]
        self._final_frequencies_gpu = cuModuleGetGlobal(module, b"final_frequencies")[0]
        self._final_phases_gpu = cuModuleGetGlobal(module, b"final_phases")[0]
        self._stream = cuStreamCreate(0)
        self._exit_stack.callback(cuStreamDestroy, self._stream)

    def __exit__(self, exc_type, exc_value, traceback):
        self._exit_stack.__exit__(exc_type, exc_value, traceback)

    @property
    def sampling_rate(self) -> float:
        return self._sampling_rate

    @property
    def time_step(self) -> float:
        return self._time_step

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

        self._bind_thread_to_current_context()

        output = np.zeros(number_samples, dtype=np.int16)
        with ExitStack() as stack:
            output_gpu = cuMemAlloc(output.nbytes)
            stack.callback(cuMemFree, output_gpu)

            amplitudes_f32 = np.array(amplitudes, dtype=np.float32)
            frequencies_f32 = np.array(frequencies, dtype=np.float32)
            phases_f32 = np.array(phases, dtype=np.float32)
            cuMemcpyHtoDAsync(
                self._amplitudes_gpu,
                amplitudes_f32.ctypes.data,
                amplitudes_f32.nbytes,
                self._stream,
            )
            cuMemcpyHtoDAsync(
                self._frequencies_gpu,
                frequencies_f32.ctypes.data,
                frequencies_f32.nbytes,
                self._stream,
            )
            cuMemcpyHtoDAsync(
                self._phases_gpu,
                phases_f32.ctypes.data,
                phases_f32.nbytes,
                self._stream,
            )
            arguments = [
                np.array([int(output_gpu)], dtype=np.uint64),
                np.array([number_samples], dtype=np.uint32),
                np.array([number_tones], dtype=np.uint32),
                np.array([self._time_step], dtype=np.float32),
            ]
            args = np.array([arg.ctypes.data for arg in arguments], dtype=np.uint64)
            number_blocks = math.ceil(number_samples / NUMBER_THREADS_PER_BLOCK)
            cuLaunchKernel(
                self._compute_static_traps_signal,
                number_blocks,
                1,
                1,
                NUMBER_THREADS_PER_BLOCK,
                1,
                1,
                0,
                self._stream,
                args.ctypes.data,
                0,
            )
            cuMemcpyDtoHAsync(
                output.ctypes.data, output_gpu, output.nbytes, self._stream
            )
            cuStreamSynchronize(self._stream)

        return output

    def generate_signal_moving_traps(
        self,
        initial_amplitudes: Sequence[float],
        final_amplitudes: Sequence[float],
        initial_frequencies: Sequence[float],
        final_frequencies: Sequence[float],
        initial_phases: Sequence[float],
        final_phases: Sequence[float],
        number_samples: NumberSamples,
        previous_step_stop: int,
        next_step_start: int,
    ) -> AWGSignalArray:
        number_tones = len(initial_amplitudes)
        if (
            not len(initial_phases)
            == len(initial_frequencies)
            == len(initial_amplitudes)
            == len(final_phases)
            == len(final_frequencies)
            == len(final_amplitudes)
            == number_tones
        ):
            raise ValueError(
                "Lengths of amplitudes, phases and frequencies must be equal."
            )

        self._bind_thread_to_current_context()

        output = np.zeros(number_samples, dtype=np.int16)
        with ExitStack() as stack:
            output_gpu = cuMemAlloc(output.nbytes)
            stack.callback(cuMemFree, output_gpu)

            self._copy_to_gpu(
                self._initial_amplitudes_gpu,
                np.array(initial_amplitudes, dtype=np.float32),
            )
            self._copy_to_gpu(
                self._final_amplitudes_gpu,
                np.array(final_amplitudes, dtype=np.float32),
            )
            self._copy_to_gpu(
                self._initial_frequencies_gpu,
                np.array(initial_frequencies, dtype=np.float32),
            )
            self._copy_to_gpu(
                self._final_frequencies_gpu,
                np.array(final_frequencies, dtype=np.float32),
            )

            self._copy_to_gpu(
                self._initial_phases_gpu,
                np.array(initial_phases, dtype=np.float32),
            )
            self._copy_to_gpu(
                self._final_phases_gpu,
                np.array(final_phases, dtype=np.float32),
            )

            arguments = [
                np.array([int(output_gpu)], dtype=np.uint64),
                np.array([number_samples], dtype=np.uint32),
                np.array([number_tones], dtype=np.uint32),
                np.array([self._time_step], dtype=np.float32),
                np.array([previous_step_stop], dtype=np.uint32),
                np.array([next_step_start], dtype=np.uint32),
            ]
            args = np.array([arg.ctypes.data for arg in arguments], dtype=np.uint64)
            number_blocks = math.ceil(number_samples / NUMBER_THREADS_PER_BLOCK)
            cuLaunchKernel(
                self._compute_moving_traps_signal,
                number_blocks,
                1,
                1,
                NUMBER_THREADS_PER_BLOCK,
                1,
                1,
                0,
                self._stream,
                args.ctypes.data,
                0,
            )
            cuMemcpyDtoHAsync(
                output.ctypes.data, output_gpu, output.nbytes, self._stream
            )
            cuStreamSynchronize(self._stream)

        return output

    def _copy_to_gpu(self, dst, src: np.ndarray):
        cuMemcpyHtoDAsync(dst, src.ctypes.data, src.nbytes, self._stream)

    def _bind_thread_to_current_context(self):
        cuCtxSetCurrent(self._context)


class NvrtcError(RuntimeError):
    pass


class CudaError(RuntimeError):
    pass
