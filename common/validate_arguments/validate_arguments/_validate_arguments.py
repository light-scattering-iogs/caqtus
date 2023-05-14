from typing import Callable, TypeVar, ParamSpec

import pydantic


class Config:
    arbitrary_types_allowed = True


_T = TypeVar("_T")
_P = ParamSpec("_P")


def validate_arguments(func: Callable[_P, _T]) -> Callable[_P, _T]:
    return pydantic.validate_arguments(func, config=Config)  # type: ignore
