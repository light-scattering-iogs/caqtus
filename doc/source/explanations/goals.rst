Goals
=====

Here are some goals and guidelines that shape the architecture of the framework.

Reproducibility
---------------

Experimental runs should be reproducible.

An experimental run is defined by 3 things:

Configuration
~~~~~~~~~~~~~

This what the user declares they are going to do before running it on the apparatus.

In our case, this is the sequence configuration and the device configurations.
They are saved in permanent storage and once a sequence has been launched, they become read-only.

It should always be possible to


It should be possible to reproduce an experiment at any time, assuming the apparatus has not changed.

If the apparatus has changed, it should at least be possible to view old configurations and sequences.

To ensure this, anything that a user can change on the experiment during their day to day operations should
be saved in configuration files.

It is discouraged to change the code controlling a device to change its behaviour on a day to day basis.
Instead, there should be a field in the device configuration that can control the behaviour and that is saved for each
sequence.

The only reasons to edit the code of a device would be to add new features or to fix bugs.

Once a sequence has been launched, it should always be possible to reopen it.

If the apparatus has not changed, it should be possible to run the sequence again without any modification.

It means that if new features are added to configurations, it should still be possible to read old configurations and
have default values for the new fields that respect the old behaviour.

Data availability
~~~~~~~~~~~~~~~~~

Raw data are saved by default such that any analysis can be redone later.

Retro-compatibility
~~~~~~~~~~~~~~~~~~~

Automation
----------

Everything a user can do with mouse and keyboard should be possible to automate with basic scripts.

Extensibility
-------------

It should be possible to add new functionalities to the experiment without changing the core code.

For example, it is possible to add a device extension or a time lane extension.

