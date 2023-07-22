def get_static_traps_cuda_program(max_number_tones: int) -> str:
    # This is a string that contains the CUDA program. It will be compiled at runtime.
    # There are three constant arrays for tone frequencies, amplitudes and phases.
    # Having the arrays defined as constant allows to bypass memory allocation and speeds up the computation. While the
    # memory is pre-allocated, the arrays are not initialized, so the values must be set before the kernel is called.
    # Note that the constant memory is limited to 64 KB, so only about 5000 tones at most can be used, which should not
    # be a problem.

    return f"""    
    __constant__ float frequencies[{max_number_tones}];
    __constant__ float amplitudes[{max_number_tones}];
    __constant__ float phases[{max_number_tones}];
    
    extern "C" __global__
    void compute_static_traps_signal(short *output, unsigned int number_samples, unsigned int number_tones, float time_step)
    {{
     float pi = 3.141592653589793;
     unsigned int tid = blockIdx.x * blockDim.x + threadIdx.x;
     float result = 0.0;
     float t = tid * time_step;
     if (tid < number_samples){{
       for(unsigned int i=0; i < number_tones; i++){{
            // We use __sinf here for speed compared to sinf, it is less accurate but that should not matter much.
            result +=  amplitudes[i] * __sinf(2 * pi * t * frequencies[i] + phases[i]);
       }}
       output[tid] = short(result * (1 << 15)); 
     }}
    }}
    """
