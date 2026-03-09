How to mark an exception as recoverable
=======================================

To make an exception recoverable and prevent it from crashing the application, you can use the :mod:`caqtus.types.recoverable_exceptions` module.

If you control the code that raises the exception
-------------------------------------------------

If you have control over the exception you are raising, raise an exception that inherits from :class:`caqtus.types.recoverable_exceptions.RecoverableException`.

The module :mod:`caqtus.types.recoverable_exceptions` defines common recoverable exceptions that you can use.
If no recoverable exception fits your use case, you can create a new exception that inherits from :class:`caqtus.types.recoverable_exceptions.RecoverableException`.

Examples:

.. code-block:: python

    from caqtus.types.recoverable_exceptions import InvalidValueError

    def set_voltage(voltage):
        if voltage < 0:
            raise InvalidValueError('Voltage must be positive')
        else:
            # Do something with the voltage

.. code-block:: python

    from caqtus.types.recoverable_exceptions import RecoverableException

    class MyCustomError(RecoverableException):
        pass

    def my_function():
        raise MyCustomError('Something went wrong')

If you don't control the code that raises the exception
-------------------------------------------------------

If you don't control the code that raises the exception, you can catch the exception and re-raise a recoverable exception with the original exception as the cause.

Example:

.. code-block:: python

    from caqtus.types.recoverable_exceptions import InvalidTypeError

    def my_function():
        try:
            # Code that raises an exception
            ...
        except TypeError as e:
            raise InvalidTypeError('Something went wrong') from e
