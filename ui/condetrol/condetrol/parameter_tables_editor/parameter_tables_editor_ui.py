# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'parameter_tables_editor.ui'
##
## Created by: Qt User Interface Compiler version 6.6.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QPushButton, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

class Ui_ParameterTablesEditor(object):
    def setupUi(self, ParameterTablesEditor):
        if not ParameterTablesEditor.objectName():
            ParameterTablesEditor.setObjectName(u"ParameterTablesEditor")
        ParameterTablesEditor.resize(848, 532)
        self._layout = QVBoxLayout(ParameterTablesEditor)
        self._layout.setObjectName(u"_layout")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setSpacing(6)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.add_button = QPushButton(ParameterTablesEditor)
        self.add_button.setObjectName(u"add_button")

        self.horizontalLayout_2.addWidget(self.add_button)

        self.delete_button = QPushButton(ParameterTablesEditor)
        self.delete_button.setObjectName(u"delete_button")

        self.horizontalLayout_2.addWidget(self.delete_button)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_2)

        self.paste_from_clipboard_button = QPushButton(ParameterTablesEditor)
        self.paste_from_clipboard_button.setObjectName(u"paste_from_clipboard_button")

        self.horizontalLayout_2.addWidget(self.paste_from_clipboard_button)

        self.copy_to_clipboard_button = QPushButton(ParameterTablesEditor)
        self.copy_to_clipboard_button.setObjectName(u"copy_to_clipboard_button")

        self.horizontalLayout_2.addWidget(self.copy_to_clipboard_button)


        self._layout.addLayout(self.horizontalLayout_2)


        self.retranslateUi(ParameterTablesEditor)

        QMetaObject.connectSlotsByName(ParameterTablesEditor)
    # setupUi

    def retranslateUi(self, ParameterTablesEditor):
        ParameterTablesEditor.setWindowTitle(QCoreApplication.translate("ParameterTablesEditor", u"Form", None))
        self.add_button.setText("")
        self.delete_button.setText("")
        self.paste_from_clipboard_button.setText(QCoreApplication.translate("ParameterTablesEditor", u"Paste from clipboard", None))
        self.copy_to_clipboard_button.setText(QCoreApplication.translate("ParameterTablesEditor", u"Copy to clipboard", None))
    # retranslateUi

