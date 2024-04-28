How to add a new device
=======================

What you need to write
-----------------------

#. Create a class that inherits from :class:`caqtus.device.runtime.Device` and implement methods to communicate with
   the instrument.

   The content of these methods will be specific to the instrument you are controlling.

   Typically, you will need to write the *__enter__*, *__exit__* methods to open and close the connection to the
   instrument at the beginning and end of the sequence.
   In addition you can write methods to update some parameters of the device before a shot.
   If you need to communicate to the device during the shot, you can write methods for that too.

   Methods for the device should take arguments in the most natural form for the device and should not care about
   translating values from user-friendly terms.

   You can test that your device works as expected by writing standalone tests for the methods you wrote.

#. Create a class that inherits from :class:`caqtus.device.configuration.DeviceConfiguration` to hold the configuration
   of the device.

   Values in the configuration should be expressed in user terms.
   For example, they can be expressed in more natural units for the user, or contain unbound
   :class:`caqtus.types.expression.Expression` objects.

   You will also need to write functions to (de)serialize the configuration to/from JSON format.
   For this you can use the module :mod:`caqtus.utils.serialization` or the `cattrs <https://catt.rs/en/stable/>`_
   library.

#. (To change) Write a function that can return the arguments to initialize the device from the configuration and
   sequence context.

#. Write or reuse a :meth:`caqtus.device.controller.DeviceController.run_shot` method that controls the device during a
   shot.

#. (To change) Write a function that can return arguments to be passed to the
   :meth:`caqtus.device.controller.DeviceController.run_shot` method from the configuration and shot context.

How to register what you wrote
------------------------------

TODO



