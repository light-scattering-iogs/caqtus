Writing a new device
====================

In this example, we will implement a new device to be integrated in an experiment.
Along the way, we will see the hierarchy of classes that make up a device extension and how they interact with different parts of the experiment.

We will here implement some sort of power source that set a voltage at the beginning of the shot and measure a current once the shot has started.

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
