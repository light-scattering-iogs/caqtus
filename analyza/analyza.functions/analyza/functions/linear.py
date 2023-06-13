def linear_function(x, a, b=0, **kwargs):
    """Compute an affine function.

    This function is defined as:
    .. math::
        f(x) = a x + b

    Args:
        x: The independent variable.
        a: The slope of the function.
        b: The intercept of the function.
    """

    return a * x + b
