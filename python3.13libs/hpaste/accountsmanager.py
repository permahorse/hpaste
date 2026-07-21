try:
    from PySide6.QtWidgets import *
    from PySide6.QtGui import *
    from PySide6.QtCore import *
except ImportError:
    from PySide2.QtWidgets import *
    from PySide2.QtGui import *
    from PySide2.QtCore import *

from . import accountsmanager_ui

from .githubauthorizator import GithubAuthorizator


class QStringCheckboxListModel(QAbstractListModel):
    def __init__(self, parent=None):
        super(QStringCheckboxListModel, self).__init__(parent)
        self.__items = []

    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            return self.__items[index.row()][1]
        elif role == Qt.CheckStateRole:
            return self.__items[index.row()][0]
        return None

    def rowCount(self, index=None):
        if index is None:
            index = QModelIndex()
        if index.isValid():
            return 0
        return len(self.__items)

    def setData(self, index, value, role):
        if not index.isValid():
            return False
        if role == Qt.CheckStateRole:
            self.__items[index.row()][0] = value
            self.dataChanged.emit(index, index, [])
            return True
        return False

    def flags(self, index):
        return Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled

    def insertRows(self, row, count, parent):
        if row < 0:
            return False
        self.beginInsertRows(parent, row, row + count - 1)
        self.__items = self.__items[:row] + [[0, '']] * count + self.__items[row:]
        self.endInsertRows()
        return True

    def removeRows(self, row, count, parent):
        if row < 0 or len(self.__items) < row + count:
            return False
        self.beginRemoveRows(parent, row, row + count - 1)
        self.__items = self.__items[:row] + self.__items[row + count:]
        self.endRemoveRows()
        return True

    def setItemList(self, items):
        assert hasattr(items, '__iter__'), "Item list must be iterable"

        self.beginResetModel()
        self.__items = list(items)
        self.endResetModel()


class AccountsManager(object):
    class __AccountsManager(QWidget):
        def __init__(self, parent, flags=0):
            super(AccountsManager.__AccountsManager, self).__init__(parent, flags)

            self.ui = accountsmanager_ui.Ui_MainWindow()
            self.ui.setupUi(self)

            self.__authModel = QStringCheckboxListModel(self)
            self.ui.authListView.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.ui.authListView.setModel(self.__authModel)

            self.__publicModel = QStringCheckboxListModel(self)
            self.ui.publicListView.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.ui.publicListView.setModel(self.__publicModel)

            # slots-signals
            self.ui.addAuthPushButton.clicked.connect(self.newAuth)
            self.ui.removeAuthPushButton.clicked.connect(self.removeAuth)
            self.ui.addPublicPushButton.clicked.connect(self.newPublic)
            self.ui.removePublicPushButton.clicked.connect(self.removePublic)
            self.ui.reinitPushButton.clicked.connect(self.reinitButtonClicked)

            self.__authModel.dataChanged.connect(self.authDataChanged)
            self.__publicModel.dataChanged.connect(self.authDataChanged)

            self.updateAuthList()
            self.updatePublicList()

        def newAuth(self):
            good = False
            try:
                good = GithubAuthorizator.newAuthorization()
            except IOError as e:
                QMessageBox.warning(self, 'could not write the account file!', 'Error: %d : %s' % e.args)
            if good:
                self.updateAuthList()

        def removeAuth(self):
            index = self.ui.authListView.currentIndex()
            good = False
            try:
                good = GithubAuthorizator.removeAuthorization(index.data())
            except IOError as e:
                QMessageBox.warning(self, 'could not write the account file!', 'Error: %d : %s' % e.args)
            if good:
                self.updateAuthList()
                msg = QMessageBox(self)
                msg.setWindowTitle('account removed from the list!')
                msg.setTextFormat(Qt.RichText)
                msg.setText(
                    "But...<br>The access token should be deleted manually from your account.<br>Please visit <a href='https://github.com/settings/tokens'>https://github.com/settings/tokens</a> and delete access tokens you don't use anymore")
                msg.exec_()

        def newPublic(self):
            good = False
            try:
                good = GithubAuthorizator.newPublicCollection()
            except IOError as e:
                QMessageBox.warning(self, 'could not write the account file!', 'Error: %d : %s' % e.args)
            if good:
                self.updatePublicList()

        def removePublic(self):
            index = self.ui.publicListView.currentIndex()
            good = False
            try:
                good = GithubAuthorizator.removePublicCollection(index.data())
            except IOError as e:
                QMessageBox.warning(self, 'could not write the account file!', 'Error: %d : %s' % e.args)
            if good:
                self.updatePublicList()

        def updateAuthList(self):
            try:
                data = GithubAuthorizator.listAuthorizations()
            except IOError as e:
                QMessageBox.warning(self, 'could not read the account file!', 'Error: %d : %s' % e.args)
            self.__authModel.setItemList([[Qt.Checked if x['enabled'] else Qt.Unchecked, x['user']] for x in data])

        def updatePublicList(self):
            try:
                data = GithubAuthorizator.listPublicCollections()
            except IOError as e:
                QMessageBox.warning(self, 'could not read the account file!', 'Error: %d : %s' % e.args)
            self.__publicModel.setItemList([[Qt.Checked if x['enabled'] else Qt.Unchecked, x['user']] for x in data])

        # Slots & Callbacks
        def reinitButtonClicked(self):
            try:
                import hpastecollectionwidget
                hpastecollectionwidget.HPasteCollectionWidget._killInstance()
            except:
                pass

        def authDataChanged(self, indextl, indexbr):
            # For now process only checked state
            isauthmodel = indextl.model() == self.__authModel
            for row in range(indextl.row(), indexbr.row() + 1):
                for col in range(indextl.column(), indexbr.column() + 1):
                    index = indextl.sibling(row, col)
                    checked = index.data(Qt.CheckStateRole)
                    name = index.data(Qt.DisplayRole)
                    if isauthmodel:
                        GithubAuthorizator.setAuthorizationEnabled(name, checked)
                    else:
                        GithubAuthorizator.setPublicCollsctionEnabled(name, checked)

    __instance = None

    def __init__(self, parent):
        if AccountsManager.__instance is None:
            AccountsManager.__instance = AccountsManager.__AccountsManager(parent, Qt.Window)
        else:
            AccountsManager.__instance.setParent(parent)
            AccountsManager.__instance.updateAuthList()
            AccountsManager.__instance.updatePublicList()

    def __getattr__(self, item):
        return getattr(AccountsManager.__instance, item)


if __name__ == '__main__':
    import sys

    # testing here
    QCoreApplication.addLibraryPath(r'C:\Program Files\Side Effects Software\Houdini 16.0.600\bin\Qt_plugins')
    qapp = QApplication(sys.argv)

    wid = AccountsManager(None)
    wid.show()

    qapp.exec_()
