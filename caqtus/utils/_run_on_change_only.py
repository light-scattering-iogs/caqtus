from dataclasses import dataclass
from typing import (
    Callable,
    TypeVar,
    ParamSpec,
    Generic,
    Optional,
    Concatenate,
    Self,
    overload,
)

_C = TypeVar("_C")
_T = TypeVar("_T")
_P = ParamSpec("_P")


@dataclass(slots=True)
class InvocationInfo(Generic[_P, _T]):
    args: _P.args
    kwargs: _P.kwargs
    return_value: _T


class RunOnChangeDescriptor(Generic[_C, _P, _T]):
    def __init__(self, func: Callable[Concatenate[_C, _P], _T]):
        self.func = func

    def __set_name__(self, owner: type[_C], name: str) -> None:
        self.name = name

    @overload
    def __get__(self, instance: None, owner: type[_C]) -> Self:
        ...

    @overload
    def __get__(self, instance: _C, owner: type[_C]) -> Callable[_P, _T]:
        ...

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            method = RunOnChangeMethod(self.func, instance)
            setattr(instance, self.name, method)
            return method


class RunOnChangeMethod(Generic[_P, _T, _C]):
    def __init__(self, func: Callable[Concatenate[_C, _P], _T], obj: _C):
        self.__func__ = func
        self.__self__ = obj
        self._invocation_info: Optional[InvocationInfo[_P, _T]] = None

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _T:
        was_previously_called = self._invocation_info is not None

        if was_previously_called:
            have_args_changed = (
                self._invocation_info.args == args
                and self._invocation_info.kwargs == kwargs
            )
            if have_args_changed:
                result = self.__func__(self.__self__, *args, **kwargs)
                self._invocation_info = InvocationInfo(args, kwargs, result)
                return result
            else:
                return self._invocation_info.return_value
        else:
            result = self.__func__(self.__self__, *args, **kwargs)
            self._invocation_info = InvocationInfo(args, kwargs, result)
            return result


def run_on_change_method(
    func: Callable[Concatenate[_C, _P], _T]
) -> RunOnChangeDescriptor[_C, _P, _T]:
    """
    Decorator that makes a method only call the underlying function if the arguments change between consecutive calls.

    When the decorated method is called the first time, the underlying function is called and the calling arguments and
    the result are stored. The next time the method is called, we compare the arguments to the previous ones. If they
    are the same, we return the result of the previous call without invoking the underlying function. If they are
    different, we call the function again, and we store the new arguments and result instead of the previous ones.

    Only the last arguments and result are stored, so interleaving calls with different arguments every other call will
    invoke the function every time.

    When comparing the arguments, the first argument `self` is ignored. Other arguments are compared using the `==`
    operator, so they don't need to be hashable or immutable.
    Calling the method with the same arguments repeatedly will always return the exact same object, so beware of
    mutating the result of the method.
    """

    return RunOnChangeDescriptor(func)  # type: ignore
