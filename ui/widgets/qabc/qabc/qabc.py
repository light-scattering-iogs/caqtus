from abc import ABCMeta

from PyQt6.QtCore import QObject


class QABCMeta(type(QObject), ABCMeta):
    pass


class QABC(QObject, metaclass=QABCMeta):
    pass
