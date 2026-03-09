Writing a new device
====================

In this example, we will implement a new device to be integrated in an experiment.
Along the way, we will see the hierarchy of classes that make up a device extension and
how they interact with different parts of the experiment.

We will here implement some sort of power source that set a voltage at the beginning of
the shot and measure a current once the shot has finished.

The goal is to write a :class:`~caqtus.extension.DeviceExtension` that can be registered
on the experiment with its
:func:`~caqtus.extension.Experiment.register_device_extension` method.
The extension contains the pieces of logic necessary to edit the device settings and
to control the device during the experiment.
The extension is not specific to a single device, but rather to a type of device.
If we have multiple power sources, we only need to create one extension.

To create it, we can start with a template:

.. code-block:: python

    from caqtus.extension import DeviceExtension

    power_source_extension = DeviceExtension(
        label="Power Source",  # A human-readable label for the type of device.
        ... # TODO: Add the rest of the required parameters.
    )

When looking at the documentation of :class:`~caqtus.extension.DeviceExtension`, we see
that it requires several other parameters, that we will fill progressively now.

configuration_type
------------------

The first parameter we need to fill is the `configuration_type`.
We need to create a class that inherits from
:class:`~caqtus.device.DeviceConfiguration`.

An instance of this class contains the persistent settings of the device, such as its IP
address, channels to use, etc.
The configuration only contains data to be stored, but it does not communicate with the
device or perform any action.

The simplest way to create this class is to use a dataclass, or here we will use
the `attrs` library to create a class with predetermined attributes.

.. note::

    It is not mandatory to use `attrs` classes, but it is useful to reduce boilerplate
    code since a lot of code can be automatically generated for these classes.

.. code-block:: python

    import attrs
    from caqtus.device import DeviceConfiguration
    from caqtus.types.expression import Expression

    @attrs.define
    class PowerSourceConfiguration(DeviceConfiguration):
        ip_address: str
        channel: int
        voltage: Expression


Instances of the :class:`PowerSourceConfiguration` class have three attributes, an IP
address to know which device to connect to, a channel number to know which channel to
use and a voltage that can be an expression to be evaluated at runtime while the
experiment.
The `Expression` type is used to allow the voltage to be defined as a string
representing a mathematical expression that the user can input in the GUI (more latter).

We can for example manually create an instance of this class to represent a single
device:

.. code-block:: python

    config = PowerSourceConfiguration(
        ip_address="192.168.137.45",
        channel=1,
        voltage=Expression("10 V + offset_voltage"),
        )



In the extension, we can then use the class itself as the `configuration_type`
parameter:

.. code-block:: python

    power_source_extension = DeviceExtension(
        ...,
        configuration_type=PowerSourceConfiguration,
        ...,
    )

We also need to provide a function that creates a default configuration when the user
adds a new device of this type.
It must be a function that takes no arguments and returns an instance of the
`configuration_type` class.

.. code-block:: python

    def create_default_configuration() -> PowerSourceConfiguration:
        return PowerSourceConfiguration(
            ip_address="xxx.xxx.xxx.xxx",
            channel=1,
            voltage=Expression("0 V"),
        )

and add it to the extension:

.. code-block:: python

    power_source_extension = DeviceExtension(
        ...,
        configuration_type=PowerSourceConfiguration,
        configuration_factory=create_default_configuration,
        ...
    )

.. note:

    If the configuration has default values for all its attributes, the class itself can
    be used as the `configuration_factory` parameter.

Talking to the instrument
-------------------------

We first need to communicate with instrument we want to control.
This is specific to which instrument you are using and you should refer to the documentation of the instrument to know how to communicate with it.

Here we will just print the command that would be sent to the instrument.

The communication with the instrument needs to be hidden behind a class that inherits from :class:`caqtus.device.Device` as in the following block:

.. code-block:: python

    import time
    from caqtus.device import Device

    class MyPowerSource(Device):
        def __init__(self, ip_address: str):
            # Here we store the parameters passed as arguments to the constructor.
            # We don't yet connect to the device.
            self.ip_address = ip_address

        def __enter__(self):
            # This method is called once at the beginning of the sequence to connect
            # to the instrument.
            print(f"Connecting to the instrument at {self.ip_address}...")
            time.sleep(1)
            print("Connected.")

        def __exit__(self, exc_type, exc_value, traceback):
            # This method is called once at the end of the sequence to disconnect
            # from the instrument.

            print("Disconnected.")

        def update_voltage(self, voltage: float) -> None:
            # This method is called for every shot of the sequence to set the output
            # voltage of the power source.

            time.sleep(0.1)
            print(f"Voltage set to {voltage} V.")

        def measure_current(self) -> float:
            # This method is called for every shot of the sequence to measure the
            # current.

            time.sleep(0.1)
            return 4.2

The class we wrote can be used in standalone mode without running the experiment.
It is useful so that we can test that the instrument is working before integrating it with the rest of the setup.

The block below shows how the class we wrote can be used:

.. code-block:: python

    currents = []

    with MyPowerSource("192.168.137.37") as power_source:
        for voltage in range(10):
            power_source.update_voltage(voltage)
            current = power_source.measure_current()
            currents.append(current)

Here the `with` statement automatically calls the `__enter__` method at the beginning of the block and the `__exit__` method at the end of the block.
This way we know that we are connected to the instrument inside the block and that we are properly disconnected at the end of the block.

We then scan the voltage and each time we measure the current.
At the end, we have a list of currents that we can plot vs voltage.


Writing an editor for the device
--------------------------------
