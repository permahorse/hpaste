# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'accountsmanager.ui'
#
# Created: Sat Jan 13 23:24:24 2018
#      by: pyside2-uic  running on PySide2 2.0.0~alpha0
#
# WARNING! All changes made in this file will be lost!

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(488, 426)
        MainWindow.setStyleSheet("QWidget#MainWindow {\n"
"    background-color : rgb(78,78,78)\n"
"}")
        self.verticalLayout = QtWidgets.QVBoxLayout(MainWindow)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.publicVerticalLayout = QtWidgets.QVBoxLayout()
        self.publicVerticalLayout.setObjectName("publicVerticalLayout")
        self.addPublicPushButton = QtWidgets.QPushButton(MainWindow)
        self.addPublicPushButton.setObjectName("addPublicPushButton")
        self.publicVerticalLayout.addWidget(self.addPublicPushButton)
        self.removePublicPushButton = QtWidgets.QPushButton(MainWindow)
        self.removePublicPushButton.setObjectName("removePublicPushButton")
        self.publicVerticalLayout.addWidget(self.removePublicPushButton)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.publicVerticalLayout.addItem(spacerItem)
        self.gridLayout.addLayout(self.publicVerticalLayout, 1, 2, 1, 1)
        self.authListView = QtWidgets.QListView(MainWindow)
        self.authListView.setObjectName("authListView")
        self.gridLayout.addWidget(self.authListView, 0, 0, 1, 1)
        self.authVerticalLayout = QtWidgets.QVBoxLayout()
        self.authVerticalLayout.setObjectName("authVerticalLayout")
        self.addAuthPushButton = QtWidgets.QPushButton(MainWindow)
        self.addAuthPushButton.setObjectName("addAuthPushButton")
        self.authVerticalLayout.addWidget(self.addAuthPushButton)
        self.removeAuthPushButton = QtWidgets.QPushButton(MainWindow)
        self.removeAuthPushButton.setObjectName("removeAuthPushButton")
        self.authVerticalLayout.addWidget(self.removeAuthPushButton)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.authVerticalLayout.addItem(spacerItem1)
        self.gridLayout.addLayout(self.authVerticalLayout, 0, 2, 1, 1)
        self.publicListView = QtWidgets.QListView(MainWindow)
        self.publicListView.setObjectName("publicListView")
        self.gridLayout.addWidget(self.publicListView, 1, 0, 1, 1)
        self.reinitPushButton = QtWidgets.QPushButton(MainWindow)
        self.reinitPushButton.setObjectName("reinitPushButton")
        self.gridLayout.addWidget(self.reinitPushButton, 2, 2, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtWidgets.QApplication.translate("MainWindow", "account manager", None, -1))
        self.addPublicPushButton.setText(QtWidgets.QApplication.translate("MainWindow", "add", None, -1))
        self.removePublicPushButton.setText(QtWidgets.QApplication.translate("MainWindow", "remove", None, -1))
        self.addAuthPushButton.setText(QtWidgets.QApplication.translate("MainWindow", "add", None, -1))
        self.removeAuthPushButton.setText(QtWidgets.QApplication.translate("MainWindow", "remove", None, -1))
        self.reinitPushButton.setText(QtWidgets.QApplication.translate("MainWindow", "re-initialize\n"
"collections", None, -1))

