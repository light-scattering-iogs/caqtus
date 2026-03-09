External resources
==================

This page contains links to external guides for some libraries that are used in the
project.
If you want to implement a new device or a new feature, it is recommended to read the
documentation of the library that is used for that feature.

PySide6
-------

We use the library `PySide6 <https://doc.qt.io/qtforpython-6/>`_ for the graphical
interface.

Widgets
"""""""

In general it is useful to know what is a widget and how a Qt application works.
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

To create classes that are used to store date (data classes), it can be useful to use
the `attrs <https://www.attrs.org/en/stable/overview.html>_` library.
The documentation is worth reading to understand how, why and when to use it.
It is not a strong requirement to use `attrs` for classes, but it can be helpful to
reduce boilerplate code.
It works well when classes are *data classes*, i.e. classes that have several attributes
and a couple methods that don't perform complex operations.
Otherwise, regular classes might be more appropriate.

Classes created with `attrs` and with type hints for their attributes can be
automatically (de)serialized using the `cattrs` library.
It also possible to create widgets automatically for such classes with
:func:`caqtus.gui.autogen.build_editor`.

Cattrs
------

When a class is created with `attrs` and with type hints for its
attributes, the `cattrs <https://catt.rs/en/stable/>`_ library can be used to
automatically generate code the serializes and deserializes the class to plain data
structures like dictionaries and lists.

`cattrs <https://catt.rs/en/stable/>`_ is a Python library that allows you to
un/structure custom objects to/from basic collections (dicts, lists, etc) that can be
stored natively by many serialization libraries.
This library is useful to put settings and configurations in permanent storage.
It is possible to customize `cattrs` to handle custom classes and types.
By default, it can handle `attrs` classes.
