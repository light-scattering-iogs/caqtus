from inspect import signature


def get_parameters(f) -> list[str]:
    return list(signature(f).parameters)[1:]
