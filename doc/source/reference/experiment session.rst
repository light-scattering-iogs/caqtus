session
=======

Description
-----------

The experiment session centralizes all access to the persistent storage of the experiment.
It is the memory of the experiment, both for the configuration used to run it and for the data acquired.
It is represented by a :py:class:`core.session.ExperimentSession` object.

It contains a file-like hierarchy of sequences.
Each path in this hierarchy is a :py:class:`core.session.SequencePath` object.
A path can be either a directory containing other paths or it can be a sequence with no children.

A sequence is represented by a :py:class:`core.session.Sequence` object.
It contains a list of shots.
Each sequence stores the configuration needed to run it on the experiment.

Data from a shot can be accessed through the :py:class:`core.session.Shot` class.
It contains the specific values of the parameters used to run it and the data acquired using this set of parameters.

Global parameters
-----------------

A session contains a unique and global set of user parameters that are shared across all sequences.

API reference
-------------

.. autoclass:: caqtus.session.ExperimentSession
    :members:

.. autoclass:: caqtus.session.ExperimentSessionMaker
    :members:
    :special-members: __call__

.. autoclass:: caqtus.session.sql.SQLExperimentSessionMaker
    :members:
