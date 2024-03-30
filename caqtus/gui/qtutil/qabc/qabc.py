from abc import ABCMeta

from PySide6.QtCore import QObject


class QABCMeta(ABCMeta, type(QObject)):
    pass


class QABC(QObject, metaclass=QABCMeta):
    pass
