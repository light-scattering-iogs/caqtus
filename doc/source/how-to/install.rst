Setup
=====

.. _howto_install:

Installation
------------

The project is only compatible with Python 3.12 and above, so make sure you have a correct python version installed.

.. note::

    You can check your python version by running the following command:

    .. code-block:: bash

        python --version

You will need to install the `caqtus-suite` python package.

.. code-block:: bash

    pip install caqtus-suite

You then need to install PostgreSQL and create a database for the project.

Once the database is created, you will need to upgrade the database schema by following the instructions in the :ref:`upgrade-database` section.

Configuration
-------------

You need to configure the experiment to use the database just created.

.. code-block:: python

    from caqtus.extension import Experiment
    from caqtus.session.sql import PostgreSQLConfig

    my_experiment = Experiment()

    my_experiment.configure_storage(
        PostgreSQLConfig(
            host="localhost",
            port=5432,
            password="password",
            user="user",
            database="database",
        )
    )
