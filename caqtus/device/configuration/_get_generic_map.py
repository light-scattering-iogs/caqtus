from typing import get_origin, get_args, Generic, Any, Optional


def get_generic_map(
    base_cls: type,
    instance_cls: type,
) -> dict[Any, Any]:
    """Get a map from the generic type paramters to the non-generic implemented types.

    Args:
        base_cls: The generic base class.
        instance_cls: The non-generic class that inherits from ``base_cls``.

    Returns:
        A dictionary mapping the generic type parameters of the base class to the
        types of the non-generic sub-class.
    """
    assert base_cls != instance_cls
    assert issubclass(instance_cls, base_cls)
    cls: Optional[type] = instance_cls
    generic_params: tuple[Any, ...]
    generic_values: tuple[Any, ...] = tuple()
    generic_map: dict[Any, Any] = {}

    # Iterate over the class hierarchy from the instance sub-class back to the base
    # class and push the non-generic type paramters up through that hierarchy.
    while cls is not None and issubclass(cls, base_cls):
        if hasattr(cls, "__orig_bases__"):
            # Generic class
            bases = cls.__orig_bases__

            # Get the generic type parameters.
            generic_params = next(
                (
                    get_args(generic)
                    for generic in bases
                    if get_origin(generic) is Generic
                ),
                tuple(),
            )

            # Generate a map from the type parameters to the non-generic types pushed
            # from the previous sub-class in the hierarchy.
            generic_map = (
                {param: value for param, value in zip(generic_params, generic_values)}
                if len(generic_params) > 0
                else {}
            )

            # Use the type map to push the concrete parameter types up to the next level
            # of the class hierarchy.
            generic_values = next(
                (
                    tuple(
                        generic_map[arg] if arg in generic_map else arg
                        for arg in get_args(base)
                    )
                    for base in bases
                    if (
                        isinstance(get_origin(base), type)
                        and issubclass(get_origin(base), base_cls)
                    )
                ),
                tuple(),
            )
        else:
            generic_map = {}

        assert isinstance(cls, type)
        cls = next(
            (base for base in cls.__bases__ if issubclass(base, base_cls)),
            None,
        )

    return generic_map
