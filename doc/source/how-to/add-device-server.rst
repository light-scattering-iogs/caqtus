.. _add-device-server:

Add a device server
===================

To add a new computer to control devices, you need to make changes in two places:

Server computer
---------------

There can be several servers, one for every computer controlling devices.
On each one, you need to run in background a script like this:

.. code-block:: python

    from caqtus.extension import Experiment
    from caqtus_devices.arbitrary_waveform_generators import ni_6738

    my_experiment = Experiment()

    # Register on the experiment all the device extensions that the server will need to
    # control.
    my_experiment.register_device_extension(ni_6738.extension)


    # Launch the device server.
    # This will run in continuous and wait for incoming connections to connect to the
    # devices.
    if __name__ == "__main__":
        my_experiment.launch_device_server(
            # When using the InsecureRPCConfiguration, the server is open to any
            # request and will execute any command received.
            # It is not recommended to use this beside a local network.
            InsecureRPCConfiguration(
                host="localhost",
                # Port must be in range 0-65535, but lower ports are usually reserved by
                 other services.
                port=65000
            ),
        )


Client computer
---------------

There is usually a single client, and it is the computer that runs the experiment
manager.
It must be running a script like this:

.. code-block:: python

    from caqtus.extension import Experiment
    from caqtus_devices.arbitrary_waveform_generators import ni_6738

    my_experiment = Experiment()

    # Register on the experiment all the device extensions that the client will need to
    # control.
    my_experiment.register_device_extension(ni_6738.extension)

    # And all the time lanes used in the experiment
    my_experiment.register_time_lane_extension(digital_time_lane_extension)

    # And the device server that was defined above.
    my_experiment.register_device_server(
        # The name of the device server.
        # If multiple servers are running, they must have different names.
        "Device server",
        InsecureRPCConfiguration(
            host="192.168.137.42",  # The IP address at which the server can be reached.
            port=65000,  # The same port as the server.
        ),
    )

    # Run the experiment server forever.
    if __name__ == "__main__":
        my_experiment.launch_experiment_server()