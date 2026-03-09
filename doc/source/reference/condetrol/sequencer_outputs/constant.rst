Constant
========

The constant node is used to configure a channel to keep a fixed value during a |shot|.

.. image:: /images/sequencer_outputs/constant_node.png
    :width: 300

The cell in the constant node can take any |expression| that evaluates to a scalar value.
The expression is evaluated for each |shot|.


Example
-------


In the example below, the output is configured to keep a constant value of 10 V.

.. list-table::

    * - .. image:: /images/sequencer_outputs/constant_graph.png
            :width: 600
    * - .. image:: /images/sequencer_outputs/constant_plot.png
            :width: 600
