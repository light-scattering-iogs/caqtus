External resources
==================

This document contains links to external libraries and resources that are extensively used in the project.
If one wants to modify significantly the code, it is recommended to skim the documentation of these libraries to understand what they can do and their design goals.

PyQt
----

We use exclusively the `PyQt <https://doc.qt.io/qtforpython-6/>`_ library for the GUI.
It is a Python binding for the `Qt` library, which is a C++ library for creating GUIs.
The `PyQt6` library is a very powerful and flexible library, and it is the most popular library for creating GUIs in Python.
It is also very well documented, and there are many tutorials and examples available online.

Model/View architecture
"""""""""""""""""""""""

For complex tree and tables widgets, we use the model/view architecture.
The python reference can be found `here <https://doc.qt.io/qtforpython-6/overviews/model-view-programming.html>`__.
This documentation contains the reference needed when working with the model/view architecture.

Jumping straight into the source code of an already working model can be overwhelming.
An introductory tutorial can be found `here <https://doc.qt.io/qtforpython-6/overviews/modelview.html>`__.
Following it and running the examples will help to get accustomed to the model/view architecture we use.
However, this tutorial is in C++, so if you want to follow it, you will need to translate the examples to Python.


Qt Designer
"""""""""""

When setting up widgets, it is often easier to use `Qt Designer <https://doc.qt.io/qt-6/qtdesigner-manual.html>`_.
This is a graphical tool that allows you to create and edit widgets and layouts much more easily than doing it in code.


Attrs
-----

`attrs <https://www.attrs.org/en/stable/>`_ is a Python library that allows you to define classes with attributes in a more concise way.
It is used in many places in the code for example for device drivers and device configurations.
The documentation is worth reading to understand how, why and when to use it.
It is not a strong requirement to use `attrs` in this project, but it can be helpful.
It works well when classes are *data classes*, i.e. classes that have several attributes and a couple methods that don't perform complex operations.
Otherwise, regular classes might be more appropriate.

Cattrs
------

`cattrs <https://catt.rs/en/stable/>`_ is a Python library that allows you to un/structure custom objects to/from basic collections (dicts, lists, etc) that can be stored natively by many serialization libraries.
This library is useful to put settings and configurations in permanent storage.
It is possible to customize `cattrs` to handle custom classes and types.
By default, it can handle `attrs` classes.

SQLAlchemy
----------

`SQLAlchemy <https://www.sqlalchemy.org/>`_ is a Python library that allows you to interact with SQL databases.
It is a very powerful library that can be used to create, modify and query databases.
It is used in the project to store device and sequence settings, as well as acquired data.

