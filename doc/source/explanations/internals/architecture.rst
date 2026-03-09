Architecture
============

The experiment control system aims to be an intermediary between the user and an existing physical apparatus, as shown
in the following diagram.

.. figure:: system_context_diagram.*
    :alt: System Context Diagram
    :align: center

    Context diagram

The system is composed of the components to configure runs, to execute them on the apparatus, to store the acquired
data, and to visualize them.

.. figure:: experiment_system_diagram.*
    :alt: Experiment Control Container
    :align: center

    Experiment control system

Each component in the diagram above represents a different process that is responsible for a specific task.

Condetrol
---------

Condetrol is the main application the user interacts with.
It is a graphical application that allows the user to configure devices and edit and launch sequences.

When the user edits a sequence, the changes are immediately saved to the database.

When the user launches a sequence, Condetrol connects to the experiment manager server and indicates it the sequence to launch.

Experiment Manager
------------------

This is background process that is responsible for controlling the experiment and running sequences.

When it receives a request to run a sequence, it will execute this :ref:`procedure <explanations/internals/executing-a-sequence:Executing a sequence>`.

While the experiment manager is running a sequence, it will send device instructions to the device server and get the data back.

It then saves the generated data to the database.

Device Server
-------------

There can be one or more device servers running in the system, possibly on different machines.

They are responsible for communicating with the physical instruments and executing the instructions sent by the experiment manager.

One device server can control multiple instruments and uses threads to communicate with them in parallel.

SnapShot
--------

This is a GUI application that allows the user to visualize the data for each shot of a sequence in real time.

GraphPlot
---------

This is a GUI application that allows the user to gather data from one or more sequences and perform analysis on it.
