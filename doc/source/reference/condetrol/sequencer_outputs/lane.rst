Lane
====

The lane node is used to configure a channel to output the values that a given lane takes during a |shot|.

.. image:: /images/sequencer_outputs/lane_node.png
    :width: 300

The cell in the lane node should be the name of the lane that should be output.

If there is no lane with the given name for the current |sequence|, the lane node
will output what is on its input port. If there is also nothing connected to the input port,
an error will be raised.

Example
-------

In the example below, the output is configured to output the values of the lane "lane 1".

.. list-table::

    * - .. figure:: /images/sequencer_outputs/lane_graph.png
            :width: 600

            Configuration of the channel.

    * - .. figure:: /images/sequencer_outputs/lane_time_lanes.png
            :width: 600

            Time lanes for the sequence under consideration.

    * - .. figure:: /images/sequencer_outputs/lane_plot.png
            :width: 600

            Output of the channel.
