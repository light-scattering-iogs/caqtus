"""This module represent a custom experiment to be used with the caqtus framework.

It can be used to configure the static configuration of the experiment and launch the
different components of the framework.

A typical use of this module would be to configure the experiment in a separate
module and then import it in the main script to launch the experiment.

For example, in a file `experiment_configuration.py`:

.. code-block:: python

    import caqtus.extension.custom as my_experiment
    from caqtus.session.sql import PostgreSQLConfig
    from caqtus_devices.spincore_pulse_blaster import spincore_pulse_blaster_extension
    from my_devices.my_device_extension import my_device_extension

    my_experiment.configure_storage(PostgreSQLConfig(...))

    my_experiment.register_device_extension(spincore_pulse_blaster_extension)
    my_experiment.register_device_extension(my_device_extension)

Then in the script to launch the experiment:

.. code-block:: python

        from experiment_configuration import my_experiment

        if __name__ == "__main__":
            my_experiment.launch_condetrol()
"""

from caqtus.device.remote_server import RemoteDeviceManager
from .._injector import CaqtusInjector
from ..time_lane_extension import (
    digital_time_lane_extension,
    analog_time_lane_extension,
    camera_time_lane_extension,
)


class _RemoteDeviceManager(RemoteDeviceManager):
    pass


_injector = CaqtusInjector()

_injector.register_remote_device_manager_class(_RemoteDeviceManager)

_injector.register_time_lane_extension(digital_time_lane_extension)
_injector.register_time_lane_extension(analog_time_lane_extension)
_injector.register_time_lane_extension(camera_time_lane_extension)


register_device_extension = _injector.register_device_extension


register_time_lane_extension = _injector.register_time_lane_extension


configure_storage = _injector.configure_storage


configure_experiment_manager = _injector.configure_experiment_manager


get_session_maker = _injector.get_session_maker


launch_condetrol = _injector.launch_condetrol

launch_experiment_server = _injector.launch_experiment_server

launch_device_server = _injector.launch_device_server


__all__ = [
    "register_device_extension",
    "register_time_lane_extension",
    "configure_storage",
    "get_session_maker",
    "launch_condetrol",
    "launch_experiment_server",
    "configure_experiment_manager",
    "launch_device_server",
]
