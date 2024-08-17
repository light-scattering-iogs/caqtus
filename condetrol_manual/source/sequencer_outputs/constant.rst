Constant
========

The constant block is used to configure a channel to keep a fixed value during a |shot|.

.. image:: img/constant_graph.png
    :width: 600


The configuration above will output a fixed value of 10 V:

.. image:: img/constant_plot.png
    :width: 600

The cell in the constant block can take any |expression| that evaluates to a scalar value.
The expression is evaluated for each |shot|.
