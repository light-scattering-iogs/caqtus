# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_ChannelOutputDialog(object):
    def setupUi(self, ChannelOutputDialog):
        if not ChannelOutputDialog.objectName():
            ChannelOutputDialog.setObjectName(u"ChannelOutputDialog")
        ChannelOutputDialog.resize(400, 300)
        self.verticalLayout = QVBoxLayout(ChannelOutputDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.buttonBox = QDialogButtonBox(ChannelOutputDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(ChannelOutputDialog)
        self.buttonBox.accepted.connect(ChannelOutputDialog.accept)
        self.buttonBox.rejected.connect(ChannelOutputDialog.reject)

        QMetaObject.connectSlotsByName(ChannelOutputDialog)
    # setupUi

    def retranslateUi(self, ChannelOutputDialog):
        ChannelOutputDialog.setWindowTitle(QCoreApplication.translate("ChannelOutputDialog", u"Dialog", None))
    # retranslateUi

