Timelanes
=========

Overview
--------

Timelanes are objects that represent a sequence of actions or values that can change over time.
A lane does not perform any evaluation of its values, it is only a container for values set by the user.

A shot on the experiment is configured by specifying a collection of timelanes, grouped in a :class:`core.session.shot.TimeLanes` object.
These timelanes contain all timing information necessary to run a shot, with placeholders for the actual values to use.

All timelane objects are subclasses of the abstract class :class:`core.session.shot.TimeLane`.

The core project provides the following timelanes:

- :class:`caqtus.session.shot.DigitalTimeLane`
- :class:`caqtus.session.shot.AnalogTimeLane`
- :class:`caqtus.session.shot.CameraTimeLane`

More lanes can be added by the user by subclassing :class:`caqtus.session.shot.TimeLane`.
See :ref:`How to add a lane` for more information.

Timelanes can directly represent the output of a device's channel, for example by having a :class:`caqtus.session.shot.DigitalTimeLane` object to indicate when a digital channel controlling a shutter or an AOM should be high or low.
But, they can also represent more abstract concepts.
For example a :class:`caqtus.session.shot.DialTimeLane` object can represent the loading of a MOT, where several digital channels are high at the same time, and some analog channels take a specific value.

API reference
-------------

.. autoclass:: caqtus.session.shot.TimeLanes

.. autoclass:: caqtus.session.shot.TimeLane

.. autoclass:: caqtus.session.shot.DigitalTimeLane

.. autoclass:: caqtus.session.shot.AnalogTimeLane

.. autoclass:: caqtus.session.shot.CameraTimeLane


