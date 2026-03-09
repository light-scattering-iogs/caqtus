# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'error_bar_view.ui'
##
## Created by: Qt User Interface Compiler version 6.6.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (
    QCoreApplication,
    QDate,
    QDateTime,
    QLocale,
    QMetaObject,
    QObject,
    QPoint,
    QRect,
    QSize,
    QTime,
    QUrl,
    Qt,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QCursor,
    QFont,
    QFontDatabase,
    QGradient,
    QIcon,
    QImage,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPalette,
    QPixmap,
    QRadialGradient,
    QTransform,
)
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QSizePolicy,
    QSpacerItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class Ui_ErrorBarView(object):
    def setupUi(self, ErrorBarView):
        if not ErrorBarView.objectName():
            ErrorBarView.setObjectName("ErrorBarView")
        ErrorBarView.resize(400, 333)
        self.verticalLayout = QVBoxLayout(ErrorBarView)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.horizontalSpacer = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.settings_button = QToolButton(ErrorBarView)
        self.settings_button.setObjectName("settings_button")

        self.horizontalLayout.addWidget(self.settings_button)

        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(ErrorBarView)

        QMetaObject.connectSlotsByName(ErrorBarView)

    # setupUi

    def retranslateUi(self, ErrorBarView):
        ErrorBarView.setWindowTitle(
            QCoreApplication.translate("ErrorBarView", "Form", None)
        )
        self.settings_button.setText(
            QCoreApplication.translate("ErrorBarView", "...", None)
        )

    # retranslateUi
