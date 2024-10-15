"""Allows to pickle exceptions with their attributes and traceback.

This module is a small modification of the `tblib` package to use the `pickle.dumps`
function to pickle the exception object instead of `exception.__reduce_ex__` method.
This allows to customize the pickling behavior by using `copyreg.pickle`.
"""

import functools
import pickle
import types
from typing import Optional

import tblib


def unpickle_traceback(tb_frame, tb_lineno, tb_next) -> Optional[types.TracebackType]:
    ret = object.__new__(tblib.Traceback)
    ret.tb_frame = tb_frame
    ret.tb_lineno = tb_lineno
    ret.tb_next = tb_next
    return ret.as_traceback()


def pickle_traceback(tb, *, get_locals=None):
    return unpickle_traceback, (
        tblib.Frame(tb.tb_frame, get_locals=get_locals),
        tb.tb_lineno,
        tb.tb_next and tblib.Traceback(tb.tb_next, get_locals=get_locals),
    )


def unpickle_exception(
    dump, cause, tb, context=None, suppress_context=False, notes=None
):
    inst = pickle.loads(dump)
    inst.__cause__ = cause
    inst.__traceback__ = tb
    inst.__context__ = context
    inst.__suppress_context__ = suppress_context
    if notes is not None:
        inst.__notes__ = notes
    return inst


def pickle_exception(obj):
    result = (
        unpickle_exception,
        (
            pickle.dumps(obj),
            obj.__cause__,
            obj.__traceback__,
            obj.__context__,
            obj.__suppress_context__,
            # __notes__ doesn't exist prior to Python 3.11; and even on Python 3.11 it
            # may be absent
            getattr(obj, "__notes__", None),
        ),
    )
    return result


def _get_subclasses(cls):
    # Depth-first traversal of all direct and indirect subclasses of cls
    to_visit = [cls]
    while to_visit:
        this = to_visit.pop()
        yield this
        to_visit += list(this.__subclasses__())


class ExceptionPickler(pickle.Pickler):
    """A pickler that can pickle exceptions with their attributes and traceback.

    To pickle the exception object, the pickler uses :func:`pickle.dumps`, so it is
    possible to customize the pickling behavior by using :func:`copyreg.pickle`.
    """

    def __init__(self, file):
        super().__init__(file)

        self.dispatch_table = {
            types.TracebackType: functools.partial(pickle_traceback, get_locals=None)
        }

    def install(self) -> None:
        """Configure the pickler to be able to dump all currently defined exceptions."""

        for exception_cls in _get_subclasses(BaseException):
            self.register(exception_cls)

    def register(self, exc_type: type[BaseException]) -> None:
        self.dispatch_table = {**self.dispatch_table, exc_type: pickle_exception}
