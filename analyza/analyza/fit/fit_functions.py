import numpy as np

def exponential_decay(t, lifetime, amplitude, background_offset=0, *args, **kwargs):
    return amplitude * np.exp(-t / lifetime) + background_offset


# noinspection NonAsciiCharacters
def exponential_saturation(t, A, τ, b=0, *args, **kwargs):
    """Compute the following function

        .. math::
        f(t) = A \exp(-t/ \tau ) - 1 ) + b
    """
    return A * (1-np.exp(-t/τ)) + b

