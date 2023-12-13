#define PI 3.141592653589793
#define TAU 6.283185307179586
#define INV_PI 0.3183098861837907
#define MAX_NUMBER_TONES 400

__constant__ float frequencies[MAX_NUMBER_TONES];
__constant__ float amplitudes[MAX_NUMBER_TONES];
__constant__ float phases[MAX_NUMBER_TONES];

extern "C" __global__
void
compute_static_traps_signal(short *output, unsigned int number_samples, unsigned int number_tones, float time_step) {
    unsigned int tid = blockIdx.x * blockDim.x + threadIdx.x;
    float result = 0.0;
    float x = time_step * TAU * tid;
    if (tid < number_samples) {
        for (unsigned int i = 0; i < number_tones; i++) {
            float phase = x * frequencies[i] + phases[i];
            result += amplitudes[i] * __sinf(phase);
        }
        output[tid] = short(result * 32767.999);
    }
}

__constant__ float initial_frequencies[MAX_NUMBER_TONES];
__constant__ float final_frequencies[MAX_NUMBER_TONES];
__constant__ float initial_amplitudes[{max_number_tones}];
__constant__ float final_amplitudes[{max_number_tones}];
__constant__ float initial_phases[{max_number_tones}];
__constant__ float final_phases[{max_number_tones}];


// Must be equal to -1 at s=0 and +1 at s=1
__device__ float amplitude_ramp(float s) {
    return -__cosf(PI * s);
}

// Must be equal to -1 at s=0 and +1 at s=1
__device__ float frequency_ramp(float s) {
    return -__cosf(PI * s);
}

__device__ float phase_ramp_sin(float s) {
    return -__sinf(PI * s) * INV_PI;
}

__device__ float reach_constant_velocity_adiabatically(float s) {
    return -2.0 / 3.0 * powf(s, 4) + (8.0 / 3.0) * powf(s, 3) - 2 * powf(s, 2) - 1.0 / 3.0 * s +
           (4.0 / 3.0) * powf(min(1.0 / 2.0, s), 4) - 8.0 / 3.0 * powf(min(1.0 / 2.0, s), 3) +
           2 * powf(min(1.0 / 2.0, s), 2) - 2.0 / 3.0 * min(1.0 / 2.0, s);
}


__device__ float phase_ramp_minimal_jolt(float s) {
    return ((s < 1.0 / 4.0) ? (
            (8.0 / 3.0) * powf(s, 4) - s
    )
                            : ((s < 3.0 / 4.0) ? (
                    -8.0 / 3.0 * powf(s, 4) + (16.0 / 3.0) * powf(s, 3) - 2 * powf(s, 2) - 2.0 / 3.0 * s -
                    1.0 / 48.0
            )
                                               : (
                                       (8.0 / 3.0) * powf(s, 4) - 32.0 / 3.0 * powf(s, 3) + 16 * powf(s, 2) -
                                       29.0 / 3.0 * s + 5.0 / 3.0
                               )));
}

// Must be the integral of frequency_ramp over s from 0 to s
__device__ float phase_ramp(float s) {
    return reach_constant_velocity_adiabatically(s);
    //return phase_ramp_sin(s);
}


extern "C" __global__
void compute_moving_traps_signal(short *output, unsigned int number_samples, unsigned int number_tones, float time_step,
                                 unsigned int previous_step_stop, unsigned int next_step_start) {
    unsigned int tid = blockIdx.x * blockDim.x + threadIdx.x;
    float s = float(tid) / float(number_samples);
    float result = 0.0;
    float T = time_step * number_samples;
    if (tid < number_samples) {
        for (unsigned int i = 0; i < number_tones; i++) {

            float mean_frequency = 0.5 * (initial_frequencies[i] + final_frequencies[i]);
            float frequency_range = 0.5 * (final_frequencies[i] - initial_frequencies[i]);
            float initial_phase =
                    initial_phases[i] + 2 * PI * previous_step_stop * time_stóep * initial_frequencies[i];
            float target_phases =
                    final_phases[i] + 2 * PI * next_step_start * time_step * final_frequencies[i];
            float phase_mismatch = target_phases - initial_phase - (2 * PI * T) * mean_frequency;
            float s0 = 0.0;
            if (frequency_range == 0.0)
                s0 = 1.0;
            else {
                float phase_remainder = fmodf(phase_mismatch, 2 * PI);
                s0 = (1.0 - phase_remainder / (2 * PI * T * frequency_range)) / (1 - phase_ramp(1.0));
            }
            float phase = 0.0;
            if (s < s0) {
                phase = initial_phase +
                        2 * PI * T * (s * mean_frequency + frequency_range * s0 * phase_ramp(s / s0));
            } else {

                phase = initial_phase + 2 * PI * T * (s * mean_frequency + frequency_range * (s - s0 +
                                                                                              s0 *
                                                                                              phase_ramp(
                                                                                                      1.0)));

            }
            float mean_amplitude = 0.5 * (initial_amplitudes[i] + final_amplitudes[i]);
            float amplitude_range = 0.5 * (final_amplitudes[i] - initial_amplitudes[i]);
            float amplitude = mean_amplitude + amplitude_range * amplitude_ramp(s);
            result += amplitude * __sinf(phase);
        }
        output[tid] = short(result * 32767.999);
    }
}