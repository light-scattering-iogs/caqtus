.. _clean-up-enter:

Clean up properly during resource acquisition
=============================================

When acquiring resources in the `__enter__` method of a context manager, it is important to ensure that the resources are properly cleaned up if an exception occurs.



In the following example, if `acquire_resource2()` raises an exception in the `__enter__` method, the `__exit__` method will not be called, and `self._resource1` will not be closed.
A similar issue occurs if `resource2.close()` raises an exception, in which case `resource1.close()` will not be called.

.. code-block:: python

    class MyDevice(Device):

        def __enter__(self) -> Self:
            self._resource1 = acquire_resource1()
            self._resource2 = acquire_resource2()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self._resource2.close()
            self._resource1.close()

To avoid this issue, you can use a :class:`contextlib.ExitStack` like in the following example.

.. code-block:: python

    class MyDevice(Device):

        def __enter__(self) -> Self:
            self._stack = contextlib.ExitStack()

            try:
                self._resource1 = acquire_resource1()
                self._stack.callback(resource1.close)
                self._resource2 = acquire_resource2()
                self._stack.callback(resource2.close)
            except:
                self._stack.close()
                raise

        def __exit__(self, exc_type, exc_val, exc_tb):
            self._stack.close()
