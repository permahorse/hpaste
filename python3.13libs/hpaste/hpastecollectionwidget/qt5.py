import hou

from PySide2.QtCore import Slot, QSortFilterProxyModel, QRegExp, Qt
from PySide2.QtWidgets import QInputDialog, QMessageBox

from .. import hpaste
from ..hcollections.collectionwidget import CollectionWidget
from ..hcollections.collectionbase import CollectionSyncError, CollectionItem
from ..hcollections.githubcollection import GithubCollection
from ..hcollections.QDoubleInputDialog import QDoubleInputDialog

from ..logger import defaultLogger as log

from urllib import error  # just for exception catching

# TODO: implement some kind of collection rescan

from ..githubauthorizator import GithubAuthorizator


class HPasteCollectionWidget(object):
    class __HPasteCollectionWidget(CollectionWidget):
        def __init__(self, parent=None):
            super(HPasteCollectionWidget.__HPasteCollectionWidget, self).__init__(parent, metadataExposedKeys=('raw_url', 'nettype'))
            for x in range(1, 5):
                self.ui.mainView.horizontalHeader().hideSection(x)

            self.__nepane = None
            self.__netType = ''

            self.__nettypeFilter = QSortFilterProxyModel(self)
            self.__nettypeFilter.setFilterKeyColumn(4)
            self.__nettypeFilter.setFilterRegExp(QRegExp("*", Qt.CaseInsensitive, QRegExp.Wildcard))
            self.appendFilter(self.__nettypeFilter)

            self.accepted.connect(self.doOnAccept)

            self.__insideAuthCallback = False
            # self.setProperty("houdiniStyle", True)
            ss = "QTableView{border : 0px solid; gridline-color: rgb(48,48,48)}"
            ss += "QHeaderView::section{border-style: none; border-bottom: 0px; border-right: 0px;}"
            self.setStyleSheet(ss)

            self.__savedNetworkViewPos = None

        def setNetworkEditor(self, pane):
            if not isinstance(pane, hou.NetworkEditor):
                pane = None

            self.__nepane = pane  # save to position pasted nodes in it
            self.__savedNetworkViewPos = pane.cursorPosition()

            if pane is None:
                nettype = '*'
                self.__netType = ''  # Used to create new snippet types
            else:
                nettype = hpaste.getChildContext(pane.pwd(), hou.applicationVersion())
                self.__netType = nettype
            self.__nettypeFilter.setFilterRegExp(QRegExp(nettype, Qt.CaseInsensitive, QRegExp.Wildcard))

        @Slot(object)
        def doOnAccept(self, item):
            if item is None:
                return
            try:
                try:  # >h16
                    hou.clearAllSelected()
                except:  # <=h15.5
                    hou.node("/obj").setSelected(False, clear_all_selected=True)
                hpaste.stringToNodes(item.content(), ne=self.__nepane, override_network_position=self.__savedNetworkViewPos)
            except RuntimeWarning as e:
                log('Warnings encountered during load:\n%s' % str(e), 2)
            except Exception as e:
                hou.ui.displayMessage("could not paste: %s" % str(e), severity=hou.severityType.Warning)

        def _addItem(self, collection):
            # Please, dont throw from here!
            try:
                nodes = hou.selectedItems()
            except:
                nodes = hou.selectedNodes()
            if len(nodes) == 0:
                QMessageBox.warning(self, 'not created', 'selection is empty, nothing to add')
                return

            while True:
                # btn,(name,desc) = (0,('1','2'))#hou.ui.readMultiInput('enter some information about new item',('name','description'),buttons=('Ok','Cancel'))
                name, desc, public, good = QDoubleInputDialog.getDoubleTextCheckbox(self, 'adding a new item to %s' % collection.name(), 'enter new item details', 'name', 'description', 'public', '', 'a snippet', False)
                if not good:
                    return

                if len(name) > 0:
                    break;  # validity check

            try:
                # print(name)
                # print(desc)
                # print(hpaste.nodesToString(nodes))
                self.model().addItemToCollection(collection, name, desc, hpaste.nodesToString(nodes), public, metadata={'nettype': self.__netType})
            except CollectionSyncError as e:
                QMessageBox.critical(self, 'something went wrong!', 'Server error occured: %s' % str(e))

        def _changeAccess(self, index):
            item = index.internalPointer()
            text, good = QInputDialog.getItem(None, 'modify item access', 'choose new access type:', ['private', 'public'], current=item.access() == CollectionItem.AccessType.public, editable=False)
            if not good:
                return
            newaccess = CollectionItem.AccessType.public if text == 'public' else CollectionItem.AccessType.private
            if newaccess == item.access():
                return
            item.setAccess(newaccess)

        def _replaceContent(self, index):
            try:
                nodes = hou.selectedItems()
            except:
                nodes = hou.selectedNodes()
            if len(nodes) == 0:
                QMessageBox.warning(self, 'cannot replace', 'selection is empty')
                return
            item = index.internalPointer()
            good = QMessageBox.warning(self, 'sure?', 'confirm that you want to replace the content of selected item "%s". This operation can not be undone.' % item.name(), QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Ok
            if not good:
                return
            try:
                item.setContent(hpaste.nodesToString(nodes))
            except CollectionSyncError as e:
                QMessageBox.critical(self, 'something went wrong!', 'Server error occured: %s' % str(e))

        def _itemInfo(self, index):
            item = index.internalPointer()
            accesstext = 'public' if item.access() == CollectionItem.AccessType.public else 'private'
            readonlytext = 'readonly' if item.readonly() else 'editable'
            info = 'name: %s\n%s\naccess: %s\n%s\n\ncollection id: %s\n\nmetadata:\n' % (item.name(), item.description(), accesstext, readonlytext, item.id())
            info += '\n'.join(('%s : %s' % (key, item.metadata()[key]) for key in item.metadata()))

            QMessageBox.information(self, 'item information', info)

        def _renameItem(self, index):
            item = index.internalPointer()
            oldname = item.name()
            olddesc = item.description()
            newname, newdesc, good = QDoubleInputDialog.getDoubleText(self, 'modify item info', 'Enter new item name and description', 'name', 'description', oldname, olddesc)
            if not good:
                return
            if newname != oldname:
                item.setName(newname)
            if newdesc != olddesc:
                item.setDescription(newdesc)

        def _removeIcon(self, index):
            ok = QMessageBox.warning(self, 'sure?', 'confirm removing Icon. This operation can not be undone.', QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Ok
            if ok:
                super(HPasteCollectionWidget.__HPasteCollectionWidget, self)._removeIcon(index)

        def _confirmRemove(self, index):
            return QMessageBox.warning(self, 'sure?', 'confirm removing the item from collection. This operation can not be undone.', QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Ok

        # a callback for authoriser
        def _authCallback(self, callbackinfo):
            auth, public, action = callbackinfo

            if self.__insideAuthCallback: return  # prevent looping
            self.__insideAuthCallback = True

            try:
                if action == 0 or (action == 2 and not auth['enabled']):
                    good = self.removeCollection(auth['user'])
                    if not good:  # means something went wrong during  removal attempt - probably async collection syncing problem. Try later
                        if public:
                            GithubAuthorizator.setPublicCollsctionEnabled(auth['user'], True)
                        else:
                            GithubAuthorizator.setAuthorizationEnabled(auth['user'], True)

                elif action == 1 or (action == 2 and auth['enabled']):
                    if public:
                        self.addCollection(GithubCollection(auth['user'], public=True), do_async=True)  # TODO: reuse some token for public access
                    else:
                        self.addCollection(GithubCollection(auth['token']), do_async=True)
            except CollectionSyncError as e:
                QMessageBox.critical(self, 'something went wrong!', 'could not add/remove collection: %s' % str(e))
            finally:
                self.__insideAuthCallback = False

    __instance = None

    def __init__(self, parent):
        if HPasteCollectionWidget.__instance is None:
            HPasteCollectionWidget.__instance = HPasteCollectionWidget.__HPasteCollectionWidget(parent)
            try:
                auths = []

                if True:
                    auths = list(GithubAuthorizator.listAuthorizations())
                ## test
                # todel = []
                # for auth in auths:
                #    if not GithubAuthorizator.testAuthorization(auth):
                #        if not GithubAuthorizator.newAuthorization(auth):
                #            todel.append(auth)
                # for d in todel:
                #    auths.remove(d)
                # For now don't force people to have their own collections
                while False and len(auths) == 0:
                    auths = list(GithubAuthorizator.listAuthorizations())
                    if len(auths) == 0:
                        if GithubAuthorizator.newAuthorization():
                            continue
                        else:
                            raise RuntimeError("No collections")
                    # test
                    todel = []
                    for auth in auths:
                        if not GithubAuthorizator.testAuthorization(auth):
                            if not GithubAuthorizator.newAuthorization(auth):
                                todel.append(auth)
                    for d in todel:
                        auths.remove(d)
            except Exception as e:
                hou.ui.displayMessage('Something went wrong.\n%s' % str(e))
                HPasteCollectionWidget.__instance = None
                raise

            for auth in auths:
                if auth['enabled']:
                    HPasteCollectionWidget.__instance.addCollection(GithubCollection(auth['token']), do_async=True)

            # now public collections
            cols = GithubAuthorizator.listPublicCollections()
            for col in cols:
                if not col['enabled']:
                    continue
                try:
                    # TODO: test if collection works
                    ptkn = None
                    if len(auths) > 0:
                        import random
                        ptkn = random.sample(auths, 1)[0]['token']
                    HPasteCollectionWidget.__instance.addCollection(GithubCollection(col['user'], public=True, token_for_public_access=ptkn), do_async=True)
                except Exception as e:
                    msg = ''
                    if isinstance(e, error.HTTPError):
                        msg = 'code %d. %s' % (e.code, e.reason)
                    elif isinstance(e, error.URLError):
                        msg = e.reason
                    else:
                        msg = str(e)
                    hou.ui.displayMessage('unable to load public collection %s: %s' % (col['user'], msg))

            # set callback
            GithubAuthorizator.registerCollectionChangedCallback((HPasteCollectionWidget.__instance, HPasteCollectionWidget.__HPasteCollectionWidget._authCallback))
        elif parent is not HPasteCollectionWidget.__instance.parent():
            log("reparenting", 0)
            HPasteCollectionWidget.__instance.setParent(parent)

    @classmethod
    def _hasInstance(cls):
        return cls.__instance is not None

    @classmethod
    def _killInstance(cls):  # TODO: TO BE RETHOUGHT LATER !! THIS GUY SHOULD GO AWAY
        # remove callback, it holds a reference to us
        GithubAuthorizator.unregisterCollectionChangedCallback((cls.__instance, HPasteCollectionWidget.__HPasteCollectionWidget._authCallback))
        cls.__instance.deleteLater()  # widget has parent, so it won't be deleted unless we explicitly tell it to
        cls.__instance = None

    def __getattr__(self, item):
        return getattr(HPasteCollectionWidget.__instance, item)
