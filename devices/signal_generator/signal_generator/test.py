import math
import time
from contextlib import ExitStack, contextmanager

import numpy as np
from cuda import cuda, nvrtc
from numpy.typing import DTypeLike

# / *float
# result = 0.0;
# for (int i=0; i < number_tones; i++){
#     result += amplitudes[i] * sin(2 * pi * frequencies[i] * times[tid] + phases[i]);
# } * /
# //, float *amplitudes, float *frequencies, float *phases, size_t number_tones)

saxpy = """
extern "C" __global__
void compute_signal(float *times, float *output, size_t number_samples, float *amplitudes, float *frequencies, float *phases, size_t number_tones)
{
 float pi = 3.141592654f;
 size_t tid = blockIdx.x * blockDim.x + threadIdx.x;
 float result = 0.0;
 float t = tid * 1.6e-9;
 if (tid < number_samples){
   for(size_t i=0; i < number_tones; i++){
        result +=  amplitudes[i] * sin(2 * pi * t * frequencies[i] + phases[i]);
   }
   output[tid] = result; 
 }
}
"""


def _check_cuda_error(err):
    if isinstance(err, cuda.CUresult):
        if err != cuda.CUresult.CUDA_SUCCESS:
            raise RuntimeError("Cuda Error: {}".format(err))
    elif isinstance(err, nvrtc.nvrtcResult):
        if err != nvrtc.nvrtcResult.NVRTC_SUCCESS:
            raise RuntimeError("Nvrtc Error: {}".format(err))
    else:
        raise RuntimeError("Unknown error type: {}".format(err))


def check_cuda_error(func):
    def wrapped(*args, **kwargs):
        err, *result = func(*args, **kwargs)
        _check_cuda_error(err)
        if len(result) == 0:
            return None
        elif len(result) == 1:
            return result[0]
        else:
            return result

    return wrapped


cuMemAlloc = check_cuda_error(cuda.cuMemAlloc)
cuMemcpyHtoDAsync = check_cuda_error(cuda.cuMemcpyHtoDAsync)
cuMemcpyDtoHAsync = check_cuda_error(cuda.cuMemcpyDtoHAsync)
cuMemFree = check_cuda_error(cuda.cuMemFree)


@contextmanager
def cuda_mem_alloc(length: int, dtype: DTypeLike):
    allocated = cuMemAlloc(length * np.dtype(dtype).itemsize)
    try:
        yield allocated
    finally:
        cuMemFree(allocated)


@contextmanager
def copy_on_device(array: np.ndarray, stream):
    with cuda_mem_alloc(array.size, array.dtype) as device_array:
        cuMemcpyHtoDAsync(
            device_array,
            array.ctypes.data,
            np.array(array.size, np.uint32) * array.dtype.itemsize,
            stream,
        )
        yield device_array


def main():
    with ExitStack() as exit_stack:
        prog = check_cuda_error(nvrtc.nvrtcCreateProgram)(
            str.encode(saxpy), b"saxpy.cu", 0, [], []
        )
        exit_stack.callback(check_cuda_error(nvrtc.nvrtcDestroyProgram), prog)

        opts = [b"--fmad=false", b"--gpu-architecture=compute_61"]
        check_cuda_error(nvrtc.nvrtcCompileProgram)(prog, 2, opts)

        ptxSize = check_cuda_error(nvrtc.nvrtcGetPTXSize)(prog)
        ptx = b" " * ptxSize
        check_cuda_error(nvrtc.nvrtcGetPTX)(prog, ptx)

        # Initialize CUDA Driver API
        check_cuda_error(cuda.cuInit)(0)

        # Retrieve handle for device 0
        cuDevice = check_cuda_error(cuda.cuDeviceGet)(0)

        # Create context
        context = check_cuda_error(cuda.cuCtxCreate)(0, cuDevice)
        exit_stack.callback(check_cuda_error(cuda.cuCtxDestroy), context)

        # Load PTX as module data and retrieve function
        ptx = np.char.array(ptx)
        # Note: Incompatible --gpu-architecture would be detected here
        module = check_cuda_error(cuda.cuModuleLoadData)(ptx.ctypes.data)
        exit_stack.callback(check_cuda_error(cuda.cuModuleUnload), module)
        kernel = check_cuda_error(cuda.cuModuleGetFunction)(module, b"compute_signal")

        number_tones = np.array(50, dtype=np.uint32)
        frequencies = np.linspace(77e6, 86e6, number_tones, dtype=np.float32)
        phases = np.linspace(0, 2 * np.pi, number_tones, dtype=np.float32)
        amplitudes = np.linspace(6400, 7000, number_tones, dtype=np.float32)

        sampling_rate = 625_000_000.0
        number_samples = np.array(625_248, dtype=np.uint32)
        print(type(number_samples))

        times = np.arange(number_samples, dtype=np.float32) / sampling_rate
        print(times.dtype)
        output = np.zeros(number_samples, dtype=np.float32)

        NUM_THREADS = 512  # Threads per block
        NUM_BLOCKS = math.ceil(number_samples / NUM_THREADS)  # Blocks per grid

        # device_frequencies = cuMemAlloc(tones_size * frequencies.itemsize)
        # exit_stack.callback(cuMemFree, device_frequencies)
        # device_amplitudes = cuMemAlloc(tones_size * amplitudes.itemsize)
        # exit_stack.callback(cuMemFree, device_amplitudes)
        # device_phases = cuMemAlloc(tones_size * phases.itemsize)
        # exit_stack.callback(cuMemFree, device_phases)

        t0 = time.perf_counter()
        stream = check_cuda_error(cuda.cuStreamCreate)(0)

        device_times = exit_stack.enter_context(copy_on_device(times, stream))
        device_output = exit_stack.enter_context(copy_on_device(output, stream))

        device_amplitudes = exit_stack.enter_context(
            copy_on_device(amplitudes, stream)
        )
        device_frequencies = exit_stack.enter_context(
            copy_on_device(frequencies, stream)
        )
        device_phases = exit_stack.enter_context(
            copy_on_device(phases, stream)
        )

        # cuMemcpyHtoDAsync(
        #     device_amplitudes,
        #     amplitudes.ctypes.data,
        #     tones_size * amplitudes.itemsize,
        #     stream,
        # )
        # cuMemcpyHtoDAsync(
        #     device_phases,
        #     phases.ctypes.data,
        #     tones_size * phases.itemsize,
        #     stream,
        # )

        args = [
            np.array([int(device_times)], dtype=np.uint64),
            np.array([int(device_output)], dtype=np.uint64),
            number_samples.astype(np.uint64),
            np.array([int(device_amplitudes)], dtype=np.uint64),
            np.array([int(device_frequencies)], dtype=np.uint64),
            np.array([int(device_phases)], dtype=np.uint64),
            number_tones.astype(np.uint64),
        ]
        args = np.array([arg.ctypes.data for arg in args], dtype=np.uint64)

        check_cuda_error(cuda.cuStreamSynchronize(stream))

        check_cuda_error(cuda.cuLaunchKernel)(
            kernel,
            NUM_BLOCKS,  # grid x dim
            1,  # grid y dim
            1,  # grid z dim
            NUM_THREADS,  # block x dim
            1,  # block y dim
            1,  # block z dim
            0,  # dynamic shared memory
            stream,  # stream
            args.ctypes.data,  # kernel arguments
            0,  # extra (ignore)
        )
        #
        cuMemcpyDtoHAsync(
            output.ctypes.data,
            device_output,
            number_samples * np.dtype("float32").itemsize,
            stream,
        )
        check_cuda_error(cuda.cuStreamSynchronize(stream))
        t1 = time.perf_counter()

        print(f"{(t1-t0) * 1e3} ms")
        print(times)
        print(output)

        # print(cuda.cudaGetErrorString(err))
        #
        # hZ = a * hX + hY
        # if not np.allclose(hOut, hZ):
        #     raise ValueError("Error outside tolerance for host-device vectors")


if __name__ == "__main__":
    main()
