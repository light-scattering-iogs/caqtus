from abc import ABCMeta
from typing import final


@final  # No subclassing of NoPublicConstructor itself.
class NoPublicConstructor(ABCMeta):
    """Metaclass that ensures a private constructor.

    If a class uses this metaclass like this::

        @final
        class SomeClass(metaclass=NoPublicConstructor):
            pass

    The metaclass will ensure that no instance can be initialized. This should always be
    used with @final.

    If you try to instantiate your class (SomeClass()), a TypeError will be thrown. Use
    _create() instead in the class's implementation.

    Raises
    ------
    - TypeError if an instance is created.
    """

    def __call__(cls, *args: object, **kwargs: object) -> None:
        raise TypeError(
            f"{cls.__module__}.{cls.__qualname__} has no public constructor"
        )

    def _create[T](cls: type[T], *args: object, **kwargs: object) -> T:
        return super().__call__(*args, **kwargs)  # type: ignore
