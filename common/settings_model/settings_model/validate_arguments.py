from inspect import getfullargspec
from typing import Callable, get_type_hints

from pydantic import parse_obj_as


def validate_argument_types(function: Callable):
    argspec = getfullargspec(function)
    arg_names = argspec.args
    if arg_names[0] == "self":
        del arg_names[0]
    type_hints = get_type_hints(function)

    def wrapped(*args, **kwargs):
        for index, arg in enumerate(args):
            name = argspec.args[index]
            type_hint = type_hints[name]
            parse_obj_as(type_hint, arg)
        return wrapped(*args, **kwargs)

    return wrapped
