import contextlib


@contextlib.contextmanager
def add_exc_note(note: str):
    """Context manager that adds a note to the exception raised in the context.

    This is a direct copy of:
    https://peps.python.org/pep-0678/#add-a-helper-function-contextlib-add-exc-note
    """

    try:
        yield
    except Exception as err:
        err.add_note(note)
        raise
