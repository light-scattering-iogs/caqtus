How to implement a new device
=============================

This guide will show you how to write a new device extension for Caqtus.






To create a device extension that can be used with your experiment, you need to create an instance of :py:class:`caqtus.extension.DeviceExtension` and fill in the required arguments.

#. `label`: put a unique name for your device extension.
#. `device_type`: subclass :py:class:`caqtus.device.runtime.Device` and implement the abstract methods.
   This class must at least implement the following methods:

   #. `__init__(self, *args, **kwargs)`: the constructor of the device extension in which you set the device attributes.
   #. `__enter__(self)`: the method that will be called to start the connection with the device using the attributes set in the constructor.
   #. `__exit__(self, exc_type, exc_value, traceback)`: the method that will be called to close the connection with the device.

   You can then add more methods to the device extension to interact with the device according to your needs.

#. `configuration_type`: create a subclass of :py:class:`caqtus.device.configuration.DeviceConfiguration` and add attributes to it that will be hold the configuration of the device.
   You can pass the created class for this argument.
