def get_traps_cuda_program(max_number_tones: int) -> str:
    # This is a string that contains the CUDA program. It will be compiled at runtime.
    # There are three constant arrays for tone frequencies, amplitudes and phases.
    # Having the arrays defined as constant allows to bypass memory allocation and speeds up the computation. While the
    # memory is pre-allocated, the arrays are not initialized, so the values must be set before the kernel is called.
    # Note that the constant memory is limited to 64 KB, so only about 5000 tones at most can be used, which should not
    # be a problem.

    return f"""    
    
    #define PI 3.141592653589793
    #define TAU 6.283185307179586
    #define INV_PI 0.3183098861837907
    
    __constant__ float frequencies[{max_number_tones}];
    __constant__ float amplitudes[{max_number_tones}];
    __constant__ float phases[{max_number_tones}];
    
    extern "C" __global__
    void compute_static_traps_signal(short *output, unsigned int number_samples, unsigned int number_tones, float time_step)
    {{
     unsigned int tid = blockIdx.x * blockDim.x + threadIdx.x;
     float result = 0.0;
     float x = time_step * TAU * tid;
     if (tid < number_samples){{
       for(unsigned int i=0; i < number_tones; i++){{
            float phase = x * frequencies[i] + phases[i];
            result +=  amplitudes[i] * __sinf(phase);
       }}
       output[tid] = short(result * 32767.999);
     }}
    }}
    
    __constant__ float initial_frequencies[{max_number_tones}];
    __constant__ float final_frequencies[{max_number_tones}];
    __constant__ float initial_amplitudes[{max_number_tones}];
    __constant__ float final_amplitudes[{max_number_tones}];
    __constant__ float initial_phases[{max_number_tones}];
    __constant__ float final_phases[{max_number_tones}];
    
    // Must be equal to -1 at s=0 and +1 at s=1
    __device__ float amplitude_ramp(float s)
    {{
        return -1.0 + 2.0 * s;
    }} 
    
    // Must be equal to -1 at s=0 and +1 at s=1
    __device__ float frequency_ramp(float s)
    {{
        return -__cosf(PI * s);
    }}
    
    // Must be the integral of frequency_ramp over s from 0 to s
    __device__ float phase_ramp(float s)
    {{
        
        return -__sinf(PI * s) * INV_PI;
    }}
    
    extern "C" __global__
    void compute_moving_traps_signal(short *output, unsigned int number_samples, unsigned int number_tones, float time_step, unsigned int previous_step_length)
    {{
     unsigned int tid = blockIdx.x * blockDim.x + threadIdx.x;
     float s = float(tid) / float(number_samples);
     float result = 0.0;
     float X = time_step * TAU * number_samples;
     if (tid < number_samples){{
       for(unsigned int i=0; i < number_tones; i++){{
            float mean_frequency = 0.5 * (initial_frequencies[i] + final_frequencies[i]);
            float frequency_range = 0.5 * (final_frequencies[i] - initial_frequencies[i]);
            float initial_phase = initial_phases[i] + TAU * previous_step_length * time_step * initial_frequencies[i];
            float phase = X * (s * mean_frequency + frequency_range * phase_ramp(s)) + initial_phase;
            float mean_amplitude = 0.5 * (initial_amplitudes[i] + final_amplitudes[i]);
            float amplitude_range = 0.5 * (final_amplitudes[i] - initial_amplitudes[i]);
            float amplitude = mean_amplitude + amplitude_range * amplitude_ramp(s);
            result +=  amplitude * __sinf(phase);
       }}
       output[tid] = short(result * 32767.999);
     }}
    }}
    

    """
