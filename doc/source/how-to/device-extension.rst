How to write a device extension
===============================

To create a device extension that can be used with your experiment, you need to create an instance of :py:class:`caqtus.extension.DeviceExtension` and fill in the required arguments.

#. Choose a unique name for your device extension.
#. Subclass :py:class:`caqtus.device.runtime.Device` and implement the abstract methods.

