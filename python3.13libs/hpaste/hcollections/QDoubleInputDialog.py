
try:
    from PySide6.QtWidgets import *
except ImportError:
    from PySide2.QtWidgets import *

class QDoubleInputDialog(QDialog):
    def __init__(self,parent=None):
        super(QDoubleInputDialog,self).__init__(parent)

        self.ui_mainLayout=QGridLayout(self)
        self.ui_text=QLabel(self)
        self.ui_label1 = QLabel(self)
        self.ui_label2 = QLabel(self)
        self.ui_line1 = QLineEdit(self)
        self.ui_line2 = QLineEdit(self)

        self.ui_buttonLayout=QHBoxLayout()
        self.ui_buttonOk = QPushButton('Ok',self)
        self.ui_buttonOk.setDefault(True)
        self.ui_buttonCancel = QPushButton('Cancel',self)
        self.ui_buttonLayout.addStretch()
        self.ui_buttonLayout.addWidget(self.ui_buttonOk)
        self.ui_buttonLayout.addWidget(self.ui_buttonCancel)

        self.ui_mainLayout.addWidget(self.ui_text, 0, 0, 1, 2)
        self.ui_mainLayout.addWidget(self.ui_label1, 1, 0)
        self.ui_mainLayout.addWidget(self.ui_label2, 2, 0)
        self.ui_mainLayout.addWidget(self.ui_line1, 1, 1)
        self.ui_mainLayout.addWidget(self.ui_line2, 2, 1)
        self.ui_mainLayout.addLayout(self.ui_buttonLayout, 4, 1)

        #Signals-Slots
        self.ui_buttonOk.clicked.connect(self.accept)
        self.ui_buttonCancel.clicked.connect(self.reject)

        #defaults
        self.ui_text.setText('Woof')
        self.ui_label1.setText('label1')
        self.ui_label2.setText('label2')

    @classmethod
    def getDoubleText(cls,parent,title,text,label1,label2,defValue1='',defValue2=''):
        dialog=QDoubleInputDialog(parent)
        dialog.setWindowTitle(title)
        dialog.ui_text.setText(text)
        dialog.ui_label1.setText(label1)
        dialog.ui_label2.setText(label2)
        dialog.ui_line1.setText(defValue1)
        dialog.ui_line2.setText(defValue2)

        res=dialog.exec_()
        return (dialog.ui_line1.text(),dialog.ui_line2.text(),res)

    @classmethod
    def getUserPassword(cls, parent, title, text, label1, label2, defValue1='', defValue2=''):
        dialog = QDoubleInputDialog(parent)
        dialog.setWindowTitle(title)
        dialog.ui_text.setText(text)
        dialog.ui_label1.setText(label1)
        dialog.ui_label2.setText(label2)
        dialog.ui_line1.setText(defValue1)
        dialog.ui_line2.setText(defValue2)
        dialog.ui_line2.setEchoMode(QLineEdit.Password)

        res = dialog.exec_()
        return (dialog.ui_line1.text(), dialog.ui_line2.text(), res)

    @classmethod
    def getDoubleTextCheckbox(cls,parent,title,text,label1,label2,label3,defValue1='',defValue2='',defCheckbox=False):
        dialog = QDoubleInputDialog(parent)
        dialog.setWindowTitle(title)
        dialog.ui_text.setText(text)
        dialog.ui_label1.setText(label1)
        dialog.ui_label2.setText(label2)
        dialog.ui_line1.setText(defValue1)
        dialog.ui_line2.setText(defValue2)
        dialog.ui_checkbox=QCheckBox(label3,dialog)
        #dialog.ui_mainLayout.removeItem(dialog.ui_buttonLayout)
        #dialog.ui_mainLayout.addLayout(dialog.ui_buttonLayout,4,1)
        dialog.ui_mainLayout.addWidget(dialog.ui_checkbox, 3, 1)

        dialog.ui_checkbox.setChecked(defCheckbox)

        res = dialog.exec_()
        return (dialog.ui_line1.text(), dialog.ui_line2.text(), dialog.ui_checkbox.isChecked(), res)
