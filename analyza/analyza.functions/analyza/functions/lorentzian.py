def lorentzian(x, x0, γ, A, b=0, **kwargs):
    """Compute a Lorentzian function.

    This function is defined as:
    .. math::
        f(x) = \\frac{A}{1 + \\left(\\frac{x - x_0}{\\gamma}\\right)^2} + b

    Args:
        x: The independent variable.
        x0: The position of the peak.
        γ: The half-width at half value of the peak.
    """

    return A / (1 + (x - x0) ** 2 / γ ** 2) + b
