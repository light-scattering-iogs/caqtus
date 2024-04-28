"""
This module defines what interface the devices must satisfy to be used in an
experiment.
For each instrument to be used on the experiment, there must be a corresponding class
inheriting from :class:`Device` that contains the low-level logic to control the actual
instrument.

The only place where actual communication to an instrument can occur during an
experiment is inside the methods of a device.

Below is a very basic usage example of a device that satisfies this protocol:

.. code-block:: python

        with RotationState(name="stage", port="COM0") as rotation_stage:
            for angle in range(0, 360, 10):
                rotation_stage.update_parameters(angle=angle)
"""

from ._device import Device, AcquisitionDevice
from ._installed_devices_discovery import load_installed_devices
from .runtime_device import RuntimeDevice

__all__ = ["Device", "RuntimeDevice", "load_installed_devices", "AcquisitionDevice"]
