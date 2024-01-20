import sys

from PyQt6.QtWidgets import QApplication, QTreeWidget

from exception_tree import create_exception_tree


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


def create_exception() -> Exception:
    exception_0 = ValueError("Value is invalid")
    exception_1 = TypeError("Type is invalid")
    exception_0.__cause__ = exception_1
    exception_3 = Exception("Exception 3")
    exception_4 = Exception("Exception 4")
    exception_4.add_note("note")
    exception_5 = Exception("Exception 5")
    exception_4.__cause__ = exception_5
    exception_2 = ExceptionGroup("Group of exceptions", [exception_3, exception_4])

    exception_1.__cause__ = exception_2
    return exception_0


def main():
    sys.excepthook = except_hook
    app = QApplication(sys.argv)
    tree = create_exception_tree(create_exception())
    tree_widget = QTreeWidget()
    tree_widget.setColumnCount(2)

    # tree_widget.hideColumn(0)
    tree_widget.setRootIsDecorated(False)

    tree_widget.addTopLevelItems(tree)
    tree_widget.expandAll()
    tree_widget.show()
    app.exec()


if __name__ == "__main__":
    main()
