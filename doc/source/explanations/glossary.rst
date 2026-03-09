Glossary
========

.. glossary::

    Sequence
        A sequence is a collection of :term:`shots<Shot>` that are executed in a specific order.

        A sequence defines a way to iterate over a set of :term:`parameters<Parameter>` and to execute a shot for each combination of parameters.

    Shot
        A shot is a single realisation of a physical experiment.

        A shot is defined by its :term:`parameters<Parameter>` and its :term:`time lanes<Time lanes>` that define the actions to execute during the shot.

    Parameter
        A parameter is a named variable that has a given value for a :term:`shot<Shot>`.

    Time lanes
        A sequence of actions to execute for each time step of a :term:`shot<Shot>`.

    Instrument
        An instrument is a physical device that is controlled by the computer during the execution of a :term:`shot<Shot>`.

    Globals
        Globals are a set of :term:`parameters<Parameter>` that are shared between all :term:`sequences<Sequence>`.

        Any change to the globals will be reflected on the future sequences, unless these sequences override the globals.

    Device server
        A computer that controls devices.

        When a sequence is launched, for each device in use, the experiment manager
        connects to the device server that controls the device.
        The experiment manager asks the device server to connect to the device and
        to execute remote commands on the device.

    Experiment manager
        Program responsible for running sequences and coordinating devices.

        The experiment manager typically runs in a background terminal in permanence.
        When a sequence is launched, either in the GUI or programmatically, the name
        of the sequence is passed to the experiment manager.
        The experiment manager then executes the shots and saves the data acquired.
