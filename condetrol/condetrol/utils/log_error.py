import logging
from functools import wraps


def log_error(logger: logging.Logger):
    def _log_error(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except Exception as err:
                logger.error(err, exc_info=True)

        return wrapped

    return _log_error
