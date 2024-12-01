.. _concepts_expression:

Expression
==========

An expression is a mathematical formula that can be evaluated.

Expressions can either be evaluated once at the beginning of a |sequence|, or multiple
times for each |shot|.

When an expression is evaluated for each |shot|, its value can be different every time
if it depends on a variable that changes between shots.

Analog expression
-----------------

An analog expression is a mathematical expression that takes either a real value or a
dimensioned value.

* ``10``: a constant value
* ``40 kHz``: a constant value with a unit
* ``(10 MHz + 20 kHz) / 2``: an algebraic formula
* ``sin(0.5)``: a formula with a function
* ``5 * red_mot.detuning``: a formula with a variable


Digital expression
------------------

A digital expression is a mathematical expression that takes only two values: `Enabled`
or `Disabled`.

It can be one of the following:

- A digital constant, such as `Enabled` or `Disabled`.
- The name of a parameter that has a digital value.
- A function that returns a digital value.

Available functions
^^^^^^^^^^^^^^^^^^^

`square_wave(x, duty=0.5)`
""""""""""""""""""""""""""




Return a periodic square waveform.

Arguments
~~~~~~~~~

- `x`: The variable over which to evaluate the waveform.

  When the fractional part of x is between 0 and `duty`, the waveform is `Enabled`.
  When the fractional part of x is between `duty` and 1, the waveform is `Disabled`.

  Must be a dimensionless analog expression.
  Can be either a scalar or a time-dependent expression.

- `duty`: The duty cycle of the square wave, optional.

  Must be an expression that evaluates to a dimensionless scalar in the interval [0,1].

Example
~~~~~~~

    `square_wave(t * 1 kHz - 0.2, 60%)` returns a square wave with a frequency of
    1 kHz, an initial phase of 0.2, and a duty cycle of 60%.

.. Warning::
   - For instruments that don't support loop instructions, the `square_wave` function
     will be unrolled. This can result in a long programming time on the instrument.
   - The period of the square wave is rounded to the nearest integer multiple of the
     instrument's time step.

.. versionadded:: 6.18.0
