.. _upgrade-database:

Upgrade the database
====================

This section describes how to upgrade the database schema if it gets out of sync with the application code.

.. warning::

    If something goes wrong during the upgrade process, you may lose data or corrupt the database.
    Make sure to back up the database before upgrading.

To upgrade the database storing the data for your experiment, you need to call the function :func:`caqtus.extension.upgrade_database` on the experiment configuration:

.. code-block:: python

    from caqtus.extension import upgrade_database
    from my_experiment_config import my_experiment

    upgrade_database(my_experiment)

.. note::

    A new database can be created by upgrading an empty database to the current version.

.. note::

    If the database was created with the `create_tables` function for `caqtus-suite<6.3.0`, you need to run this function before upgrading the database:

    .. code-block:: python

        from caqtus.extension import stamp_database
        from my_experiment_config import my_experiment

        stamp_database(my_experiment)

    It must not be called if you created the database by upgrading an empty database, as is the recommended way for `caqtus-suite>=6.3.0`.
