.. _upgrade-database:

Upgrade the database
====================

This section describes how to upgrade the database schema if it gets out of sync with the application code.

.. warning::

    If something goes wrong during the upgrade process, you may lose data or corrupt the database.
    Make sure to back up the database before upgrading.

To upgrade a postgres database, you need to call the function :func:`caqtus.extension.upgrade_database` on the experiment configuration:

.. code-block:: python

    from caqtus.extension import upgrade_database
    from my_experiment_config import my_experiment

    upgrade_database(my_experiment)
