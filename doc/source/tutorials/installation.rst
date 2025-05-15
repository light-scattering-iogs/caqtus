Installation
============

Installing caqtus
-----------------

You first need to install the `caqtus-suite` python package.

.. code-block:: bash

    pip install caqtus-suite

This will install the latest version of the package and its dependencies in the current python environment.
If you decide to use caqtus in the long run, it is advised to create a virtual environment for the project to avoid
conflicts with other packages, and to ensure isolation from the system python packages.
Using a package manager to do this is recommended, for example `uv`.

Configuring the database
------------------------

The project needs a database to store the data produced by the experiment.
In this section, we will use a simple SQLite database, where everything is stored in a single file.
If you plan to acquire a lot of data (more than a few 100 MB), or want to access the database from multiple computers,
it is recommended to use a PostgreSQL database instead (:ref:`setup-postgresql`).


