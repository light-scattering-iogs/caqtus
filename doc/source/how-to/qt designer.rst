How to use Qt Designer to create a new widget
=============================================

Qt designer generates `.ui` files, which can be converted to Python source code using the module `PyQt6.uic.pyuic`.
For example by running the following command in the terminal:

.. code-block:: bash

    pyside6-uic mywidget.ui -o mywidget_ui.py

This will generate a file `mywidget_ui.py` containing the class `Ui_mywidget` which can be used to create the widget in Python.

To use the generated class, you can use the following code:

.. code-block:: python

    from mywidget_ui import Ui_MyWidget

    class MyWidget(QDialog, Ui_MyWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setupUi(self)
