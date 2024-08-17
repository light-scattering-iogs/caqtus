.. _concepts_expression:

Expression
==========

An expression is a mathematical formula that can be replaced by a value.

Expressions can look like this:

* ``10``: a constant value
* ``40 kHz``: a constant value with a unit
* ``(10 MHz + 20 kHz) / 2``: an algebraic formula
* ``sin(0.5)``: a formula with a function
* ``5 * red_mot.detuning``: a formula with a variable

Expressions can either be evaluated once at the beginning of a |sequence|, or multiple times for each |shot|.

When an expression is evaluated for each |shot|, its value can be different every time if it depends on a variable that changes between shots.
