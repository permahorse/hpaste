if __name__ == '__main__':  # very old testing crap
    import os

    os.environ['PATH'] = r'C:\Program Files\Side Effects Software\Houdini 16.0.600\bin' + r';C:\Program Files\Side Effects Software\Houdini 16.0.600\houdini\dso;' + os.environ['PATH']
    os.environ['HOUDINI_USER_PREF_DIR'] = r'C:\Users\User\Documents\houdini16.0'

try:
    from PySide6.QtWidgets import *
    from PySide6.QtGui import *
    from PySide6.QtCore import *
except ImportError:
    from PySide2.QtWidgets import *
    from PySide2.QtGui import *
    from PySide2.QtCore import *

import time
import random
import string
import copy
from . import hpastewebplugins as hpw
from . import hpasteoptions


class ConnectionCheckerThread(QThread):
    workdone = Signal(tuple)

    def __init__(self, cls, parent=None):
        super(ConnectionCheckerThread, self).__init__(parent)
        self.__cls = cls
        self.__result = None

    def getResult(self):
        return self.__result

    def run(self):
        s = ''.join([random.choice(string.ascii_letters) for x in range(2 ** 15)])
        try:
            packer = self.__cls()
            starttime = time.time()
            rs = packer.webUnpackData(packer.webPackData(s))
            if rs == s:
                res = (self.__cls.__name__, 0, time.time() - starttime)
            else:
                res = (self.__cls.__name__, 2, 0.0)
        except:
            res = (self.__cls.__name__, 1, 0.0)
        self.__result = res
        self.workdone.emit(res)


class PluginListModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super(PluginListModel, self).__init__(parent)

        self._plist = [[x, ConnectionCheckerThread(x), None] for x in copy.copy(hpw.pluginClassList)]
        for x in self._plist:
            x[1].workdone.connect(self.checkerReturned)
            x[1].start()

    def rowCount(self, index):
        return len(self._plist)

    def columnCount(self, index):
        return 3

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole or orientation != Qt.Horizontal:
            return None
        if section == 0:
            return 'priority'
        elif section == 1:
            return 'name'
        elif section == 2:
            return 'status'
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        checkres = (QColor(0, 0, 0), 'Unknown')
        if index.column() == 2 and role == Qt.DisplayRole or role == Qt.EditRole or role == Qt.DecorationRole:
            # we don't really need edit role here, but just to keep things straight, failsafe and readable..
            pitem = self._plist[index.row()]
            if pitem[1] is None:
                res = pitem[2]
                if res is None:
                    checkres = (QColor(255, 16, 16), 'Error')
                else:
                    if res[0] == 0:
                        checkres = (QColor(16, 255, 16), 'Valid %.2f' % res[1])
                    else:
                        checkres = (QColor(255, 16, 16), 'Broken')
            else:
                checkres = (QColor(255, 255, 16), 'Checking...')

        if role == Qt.DisplayRole or role == Qt.EditRole:
            pitem = self._plist[index.row()]
            if index.column() == 0:
                return pitem[0].speedClass()
            elif index.column() == 1:
                return pitem[0].__name__
            elif index.column() == 2:
                return checkres[1]
        elif role == Qt.DecorationRole:
            if index.column() == 2:
                return checkres[0]
        return None

    def setData(self, index, value, role=Qt.DisplayRole):
        if role == Qt.EditRole:
            className = self.data(index.sibling(index.row(), 1))
            try:
                hpasteoptions.setOption('hpasteweb.plugins.%s.speed_class' % className, value)

                self.dataChanged.emit(index, index, [])

            except Exception as e:
                print(e)
                return False
            return True
        return False

    def flags(self, index):
        flags = Qt.ItemIsEnabled
        if index.column() == 0:
            flags |= Qt.ItemIsEditable
        return flags

    # SLOTS
    @Slot(tuple)
    def checkerReturned(self, res):
        name, code, etime = res
        rows = [i for i, x in enumerate(self._plist) if x[0].__name__ == name]
        if len(rows) != 1:
            return
        row = rows[0]

        thread = self._plist[row][1]
        if thread is not None:
            # if not thread.isFinished():thread.quit() #That would be really strange though
            thread.wait()
            thread.deleteLater()
            self._plist[row][1] = None
        self._plist[row][2] = (code, etime)

        index = self.index(row, 2)
        self.dataChanged.emit(index, index, [])


class OptionsDialog(object):
    class __OptionsDialog(QWidget):
        def __init__(self, parent=None):
            super(OptionsDialog.__OptionsDialog, self).__init__(parent, Qt.Window)
            self.__optionsReread = False
            self.resize(312, 560)
            self.setObjectName("MainWindow")

            self.ui_layout = QVBoxLayout(self)
            self.ui_table = QTableView(self)

            self.ui_layout.setContentsMargins(0, 0, 0, 0)
            self.ui_layout.addWidget(self.ui_table)

            self.__model = PluginListModel(self)
            self.__proxymodel = QSortFilterProxyModel(self)
            self.__proxymodel.setSourceModel(self.__model)
            self.__proxymodel.setDynamicSortFilter(True)
            self.ui_table.setModel(self.__proxymodel)

            self.__proxymodel.sort(0, Qt.DescendingOrder)
            self.ui_table.horizontalHeader().resizeSection(0, 56)
            self.ui_table.horizontalHeader().resizeSection(1, 192)
            self.ui_table.horizontalHeader().resizeSection(2, 92)
            self.ui_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            # self.ui_table.horizontalHeader().setVisible(False)
            self.ui_table.verticalHeader().setVisible(False)

            self.ui_resetButton = QPushButton("rerun tests", self)
            self.ui_layout.addWidget(self.ui_resetButton)
            self.ui_resetButton.clicked.connect(self.reset)

            self.ui_hpastebox = QGroupBox("hpaste options", self)
            self.ui_hpastebox.setObjectName("hpasteBox")
            self.ui_hpasteboxLayout = QVBoxLayout(self.ui_hpastebox)
            self.ui_layout.addWidget(self.ui_hpastebox)

            self.ui_hpastebox_copy = QGroupBox("copy", self)
            self.ui_hpastebox_copyLayout = QVBoxLayout(self.ui_hpastebox_copy)
            self.ui_hpasteboxLayout.addWidget(self.ui_hpastebox_copy)

            self.ui_saveHdasToggle = QCheckBox("Save definitions for non-standard assets to snippet", self)
            self.ui_saveHdasToggle.toggled.connect(self.togglesCallback)
            self.ui_hpastebox_copyLayout.addWidget(self.ui_saveHdasToggle)

            self.ui_stripmeta = QCheckBox('Strip metadata from the code', self)
            self.ui_stripmeta.toggled.connect(self.togglesCallback)
            self.ui_hpastebox_copyLayout.addWidget(self.ui_stripmeta)

            self.ui_encLayout = QHBoxLayout()

            self.ui_encLabel = QLabel('encryption type:', self)
            self.ui_encLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            self.ui_encLayout.addWidget(self.ui_encLabel)

            self.ui_encryption = QComboBox(self)
            self.ui_encryption.addItems(['None', 'AES-CBC'])
            self.ui_encryption.setEditable(False)
            self.ui_encryption.currentTextChanged.connect(self.encchangedCallback)

            self.ui_encLayout.addWidget(self.ui_encryption)
            self.ui_hpastebox_copyLayout.addLayout(self.ui_encLayout)

            self.ui_hpastebox_paste = QGroupBox("paste", self)
            self.ui_hpastebox_pasteLayout = QVBoxLayout(self.ui_hpastebox_paste)
            self.ui_hpasteboxLayout.addWidget(self.ui_hpastebox_paste)

            self.ui_ignoreWhenExists = QCheckBox("Ignore assets in snippets if definition is already installed in session", self)
            self.ui_ignoreWhenExists.toggled.connect(self.togglesCallback)
            self.ui_hpastebox_pasteLayout.addWidget(self.ui_ignoreWhenExists)

            self.ui_forcePreferred = QCheckBox("Force definitions in the snippet to be prefered", self)
            self.ui_forcePreferred.toggled.connect(self.togglesCallback)
            self.ui_hpastebox_pasteLayout.addWidget(self.ui_forcePreferred)

            self.ui_ignore_houversion_warning = QCheckBox("Ignore Houdini version mismatch warning", self)
            self.ui_ignore_houversion_warning.toggled.connect(self.togglesCallback)
            self.ui_hpastebox_pasteLayout.addWidget(self.ui_ignore_houversion_warning)

            stsh = "QWidget#MainWindow {\n    background-color : rgb(58,58,58);\n}\n"

            if QDir(":/qt-project.org/styles/commonstyle/images/").exists():  # this was introduced to workaround a bug with one of houdini linux builds that had a bug of missing standard icons in some stylesheet cases
                stsh += '''
QCheckBox::indicator:checked{
    image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-apply-16.png);
}
QCheckBox::indicator:unchecked{
    image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-cancel-16.png);
}
'''
            elif QDir(":/trolltech/styles/commonstyle/images/").exists():
                stsh += '''
QCheckBox::indicator:checked{
    image: url(:/trolltech/styles/commonstyle/images/standardbutton-apply-16.png);
}
QCheckBox::indicator:unchecked{
    image: url(:/trolltech/styles/commonstyle/images/standardbutton-cancel-16.png);
}
'''
            self.setStyleSheet(stsh)

            self.rereadSettings()

        @Slot()
        def reset(self):
            self.__model = PluginListModel(self)
            self.__proxymodel.setSourceModel(self.__model)

        def rereadSettings(self):
            self.__optionsReread = True
            try:
                self.ui_saveHdasToggle.setChecked(hpasteoptions.getOption('hpaste.transfer_assets', True))
                self.ui_stripmeta.setChecked(hpasteoptions.getOption('hpaste.strip_metadata', False))
                self.ui_ignoreWhenExists.setChecked(hpasteoptions.getOption('hpaste.ignore_hdas_if_already_defined', True))
                self.ui_forcePreferred.setChecked(hpasteoptions.getOption('hpaste.force_prefer_hdas', False))
                self.ui_ignore_houversion_warning.setChecked(hpasteoptions.getOption('hpaste.ignore_houversion_warning', False))
                self.ui_encryption.setCurrentText(hpasteoptions.getOption('hpasteweb.encryption_type', 'None'))
            finally:
                self.__optionsReread = False

        @Slot(str)
        def encchangedCallback(self, newtext):
            if self.__optionsReread:
                return
            hpasteoptions.setOption('hpasteweb.encryption_type', newtext)

        @Slot(bool)
        def togglesCallback(self, state):
            if self.__optionsReread:
                return
            sender = self.sender()
            if sender is self.ui_saveHdasToggle:
                hpasteoptions.setOption('hpaste.transfer_assets', state)
            if sender is self.ui_stripmeta:
                hpasteoptions.setOption('hpaste.strip_metadata', state)
            if sender is self.ui_ignoreWhenExists:
                hpasteoptions.setOption('hpaste.ignore_hdas_if_already_defined', state)
            if sender is self.ui_forcePreferred:
                hpasteoptions.setOption('hpaste.force_prefer_hdas', state)
            if sender is self.ui_ignore_houversion_warning:
                hpasteoptions.setOption('hpaste.ignore_houversion_warning', state)

    __instance = None

    def __init__(self, parent=None):
        if OptionsDialog.__instance is None:
            OptionsDialog.__instance = OptionsDialog.__OptionsDialog(parent)
        else:
            OptionsDialog.__instance.setParent(parent)

    def __getattr__(self, item):
        return getattr(OptionsDialog.__instance, item)


if __name__ == '__main__':
    import sys

    QCoreApplication.addLibraryPath(r'C:\Program Files\Side Effects Software\Houdini 16.0.600\bin\Qt_plugins')
    qapp = QApplication(sys.argv)

    mw = OptionsDialog()
    mw.show()

    qapp.exec_()
