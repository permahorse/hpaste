from ..logger import defaultLogger as log

try:
    from PySide6.QtCore import *
    from PySide6.QtWidgets import *
    from PySide6.QtGui import *
except ImportError:
    from PySide2.QtCore import *
    from PySide2.QtWidgets import *
    from PySide2.QtGui import *

from .QDropdownWidget import QDropdownWidget

from . import collectionbase


class CollectionListerThread(QThread):
    workdone = Signal(tuple)
    workerror = Signal(tuple)

    def __init__(self, collection, parent=None):
        assert isinstance(collection, collectionbase.CollectionBase), 'collection must be a collection'
        super(CollectionListerThread, self).__init__(parent)
        self.__collection = collection
        self.__stopMutex = QMutex()
        self.__skip = False
        self.__emitted = False

    def stop(self):
        """
        signal thread to ditch it's data
        :return: wether stop was successful (True), or signal was already emitted (False)
        """
        self.__stopMutex.lock()
        self.__skip = True
        self.__stopMutex.unlock()
        return not self.__emitted

    def run(self):
        """
        worker part. will be executed in a separate thread on thread.start()
        :return: None
        """
        try:
            tmplist = self.__collection.list()
        except Exception as e:
            self.__stopMutex.lock()  # TODO: so much more python-style to wrap this mutex into a with-statement
            try:
                if not self.__skip:
                    self.workerror.emit((self.__collection, "Error listing the collection: %s" % str(e)))
                    self.__emitted = True
            except:
                pass
            self.__stopMutex.unlock()
            return

        self.__stopMutex.lock()
        try:
            if not self.__skip:
                self.workdone.emit((self.__collection, tmplist))
                self.__emitted = True
        except:
            pass
        self.__stopMutex.unlock()


class SnippetCollectionModel(QAbstractTableModel):
    asyncLoadingStarted = Signal()
    asyncLoadingFinished = Signal()

    def __init__(self, collectionsList, parent=None, metadataExposedKeys=()):
        assert isinstance(metadataExposedKeys, list) or isinstance(metadataExposedKeys, tuple), 'metadataExposeKeys should be a collection of string keys'

        super(SnippetCollectionModel, self).__init__(parent)
        self.__collections = list(collectionsList)
        self.__itemList = []  # This list should be 1-to-1 corresponding to model's rows

        self.__metadataExposedKeys = tuple(metadataExposedKeys)
        self.__asyncProcessedCollections = {}  # a dict of collection:thread that is being calculated currently async

        self.rescanCollections()

    def addCollection(self, collection):
        assert isinstance(collection, collectionbase.CollectionBase), 'collection must be a collection'
        if collection in self.__collections or collection in self.__asyncProcessedCollections.keys(): return
        self.__collections.append(collection)
        tmplist = collection.list()
        if len(tmplist) == 0:
            return
        nextid = len(self.__itemList)
        self.beginInsertRows(QModelIndex(), nextid, nextid + len(tmplist) - 1)
        self.__itemList += tmplist
        self.endInsertRows()

    def addCollectionAsync(self, collection):
        assert isinstance(collection, collectionbase.CollectionBase), 'collection must be a collection'
        if collection in self.__collections or collection in self.__asyncProcessedCollections.keys(): return

        firstone = len(self.__asyncProcessedCollections) == 0
        thread = CollectionListerThread(collection, self)
        self.__asyncProcessedCollections[collection] = thread
        thread.workdone.connect(self.__addCollectionAsync_finish)
        thread.workerror.connect(self.__addCollectionAsync_error)
        thread.finished.connect(thread.deleteLater)
        if firstone:
            self.asyncLoadingStarted.emit()
        thread.start()

    def asyncLoadingCollectionsCount(self):
        return len(self.__asyncProcessedCollections)

    @Slot(tuple)
    def __addCollectionAsync_finish(self, threaddata):
        """
        This should only be called by thread finish signal
        :param collist: (collection, list/tuple of collection items)
        :return:
        """
        collection, itemlist = threaddata

        self.__asyncProcessedCollections[collection].wait()
        del self.__asyncProcessedCollections[collection]  # delete from pending list

        assert isinstance(itemlist, list) or isinstance(itemlist, tuple), 'itemlist argument must be a list'
        self.__collections.append(collection)
        if len(itemlist) == 0:
            return
        nextid = len(self.__itemList)
        self.beginInsertRows(QModelIndex(), nextid, nextid + len(itemlist) - 1)
        self.__itemList += itemlist
        self.endInsertRows()
        if len(self.__asyncProcessedCollections) == 0: self.asyncLoadingFinished.emit()

    @Slot(tuple)
    def __addCollectionAsync_error(self, threaddata):
        """
        This should only be called by thread error signal
        :param threaddata: (collection, string error message)
        :return:
        """
        collection, errormessage = threaddata

        self.__asyncProcessedCollections[collection].wait()
        del self.__asyncProcessedCollections[collection]  # delete from pending list

        log("Collection %s failed to load: %s" % (collection.name(), errormessage), 3)
        if len(self.__asyncProcessedCollections) == 0:
            self.asyncLoadingFinished.emit()

    def removeCollection(self, collection):
        """
        removes collection from model's collection list
        :param collection: collection instance or collection name (str)
        :return: True on success, False in case not all matching collections were deleted due to threading issues. in case of big errors - raises
        """
        # TODO: check pending collections too!
        assert isinstance(collection, collectionbase.CollectionBase) or isinstance(collection, str), 'collection must be a collection, or a string'
        if isinstance(collection, str):
            matchcollections = [x for x in self.__collections if x.name() == collection]
            matchcollections += [x for x in self.__asyncProcessedCollections.keys() if x.name() == collection]
        else:
            if collection in self.__collections or collection in self.__asyncProcessedCollections.keys():
                matchcollections = [collection]
            else:
                matchcollections = []

        result = True
        for mcollection in matchcollections:
            if mcollection in self.__collections:
                # collect indices to remove (from highest to lowedt i)
                remids = []

                for i, item in enumerate(self.__itemList):
                    if item.collection() == mcollection:
                        remids.insert(0, i)

                for i in remids:
                    self.removeRows(i, 1, QModelIndex(), affectCollections=False)

                self.__collections.remove(mcollection)
            else:  # so mcollection is in async ones
                notemitted = self.__asyncProcessedCollections[mcollection].stop()
                if notemitted:  # stop successful before signal was emitted
                    # so no signal will be emitted, thread will be deleted on finish, so we just forget about it
                    del self.__asyncProcessedCollections[mcollection]
                else:  # now this is a tricky one: signal was emitted, so it happened during execution of this function most probably
                    # actually i dunno how to handle this...
                    result = False
        return result

    def addItemToCollection(self, collection, desiredName, description, content, public, metadata=None):
        """
        Adds item to collection added to this model
        This will safely update model to incorporate item
        if you update collection independantly from model - the model will have no idea that collection has changed therefore will not be updated
        :param collection: collection already added to the model
        :param desiredName: desired name of the new item (real name may be different due to enforced name uniqueness)
        :param description: description of the item
        :param content: hpaste content of the item
        :param public: publicity of the access
        :param metadata: collection type dependant generic metadata that will be applied to the item
        :return:
        """
        if collection not in self.__collections:
            raise ValueError('collection must belong to the model')
        access = collectionbase.CollectionItem.AccessType.public if public else collectionbase.CollectionItem.AccessType.private
        newitem = collection.addItem(desiredName, description, content, access, metadata=metadata)

        nextid = len(self.__itemList)
        self.beginInsertRows(QModelIndex(), nextid, nextid)
        self.__itemList.append(newitem)
        self.endInsertRows()

    def removeItem(self, vitem):
        pass  # TODO: do, vitem should be able to be different type of item indication
        if isinstance(vitem, QModelIndex):
            self.removeRow(vitem.row(), 1, QModelIndex())

    def removeRows(self, row, count, parent, affectCollections=True):  # TODO: this way of default affecting collection seem to be pretty misleading...
        lastrow = row + count - 1
        if parent != QModelIndex() or count == 0 or lastrow >= self.rowCount(parent):
            return False

        self.beginRemoveRows(parent, row, lastrow)
        everythingIsBad = False
        for i in range(count):
            try:
                if affectCollections:
                    self.__itemList[row + i].removeSelf()
                else:
                    self.__itemList[row + i].invalidate()
            except:
                everythingIsBad = True
                break
        else:
            self.__itemList = self.__itemList[:row] + self.__itemList[row + count:]
        self.endRemoveRows()

        return not everythingIsBad

    def collections(self):
        return tuple(self.__collections)

    def rescanCollections(self):
        # TODO: IF this ever gets usefull (now it is only called with empty collection list) - make an async version
        if len(self.__itemList) > 0:
            self.beginRemoveRows(QModelIndex(), 0, len(self.__itemList) - 1)
            self.__itemList = []
            self.endRemoveRows()

        templist = []
        for collection in self.__collections:
            templist += collection.list()

        self.beginInsertRows(QModelIndex(), 0, len(templist) - 1)
        self.__itemList = templist
        self.endInsertRows()

    def columnCount(self, index=None):
        if index is None:
            index = QModelIndex()
        if index.isValid():
            return 0
        # name,desc,id + metadatakeys
        return 3 + len(self.__metadataExposedKeys)

    def rowCount(self, index=None):
        if index is None:
            index = QModelIndex()
        if index.isValid():
            return 0
        return len(self.__itemList)

    def index(self, row, col, parent):
        if parent != QModelIndex():
            return QModelIndex()
        return self.createIndex(row, col, self.__itemList[row])

    def data(self, index, role=Qt.DisplayRole):

        if role == Qt.DisplayRole:
            if index.column() == 0:
                return self.__itemList[index.row()].name()
            elif index.column() == 1:
                return self.__itemList[index.row()].description()
            elif index.column() == 2:
                return self.__itemList[index.row()].id()
            else:
                metadata = self.__itemList[index.row()].metadata()
                key = self.__metadataExposedKeys[index.column() - 3]
                if key in metadata:
                    return metadata[key]
                else:
                    return ''
        elif role == Qt.ToolTipRole:
            if index.column() == 0:
                return self.__itemList[index.row()].description()
        elif role == Qt.UserRole and 'iconpixmap' in self.__itemList[index.row()].metadata():  # UserRole instead of DecoratorRole cuz of strange QtWarning on Windows at first item show only when trying to prevent default delegate painter from drawint decorator.
            pixmap = self.__itemList[index.row()].metadata()['iconpixmap']
            if isinstance(pixmap, tuple):  # if image was loaded - information for QPixmap creation is passed, not the actual QPixamp cuz loading might have been done in a different thread
                pix = QPixmap()
                pix.loadFromData(*pixmap)
                pixmap = pix
                self.__itemList[index.row()].metadata()['iconpixmap'] = pixmap
            return pixmap
        return None


class ScalingImageStyledItemDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        size = super(ScalingImageStyledItemDelegate, self).sizeHint(option, index)
        if index.data(Qt.UserRole) is not None:
            size += QSize(size.height(), 0)
        return size

    def paint(self, painter, option, index):
        pixmap = index.data(Qt.UserRole)

        if index.column() == 0 and pixmap is not None:
            msize = min(option.rect.height(), option.rect.width())
            imgrect = QRect(option.rect.topLeft(), QSize(msize, msize))

            oldhints = painter.renderHints()
            painter.setRenderHints(QPainter.SmoothPixmapTransform)
            painter.drawPixmap(imgrect, pixmap)
            painter.setRenderHints(oldhints)

            option.rect.adjust(msize, 0, 0, 0)

        super(ScalingImageStyledItemDelegate, self).paint(painter, option, index)


class CollectionWidget(QDropdownWidget):
    def __init__(self, parent=None, metadataExposedKeys=()):
        super(CollectionWidget, self).__init__(parent)
        self.setProperty("houdiniStyle", True)  # for some unknown reason it works only if it's here or higher. TODO: find out why, move to hpastecollectionwidget
        self.setModel(SnippetCollectionModel([], self, metadataExposedKeys))

        self.ui.mainView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.mainView.customContextMenuRequested.connect(self.showContextMenu)
        self.ui.mainView.setItemDelegateForColumn(0, ScalingImageStyledItemDelegate(self))
        self.__openImageDialog = None

        self.ui.loadingLabel = QLabel("loading...", self)
        smallFont = QFont(self.font())
        smallFont.setItalic(True)
        smallFont.setPointSize(8)
        self.ui.loadingLabel.setFont(smallFont)
        self.ui.mainLayout.insertWidget(1, self.ui.loadingLabel, alignment=Qt.AlignCenter)
        self.ui.loadingLabel.hide()
        self.model().asyncLoadingStarted.connect(lambda sobj=self: sobj.ui.loadingLabel.show() or sobj.adjustSize())
        self.model().asyncLoadingFinished.connect(lambda sobj=self: sobj.ui.loadingLabel.hide() or sobj.adjustSize() or sobj.sort(0))

    def rescanCollections(self):
        """
        shortcut to self.model()rescanCollection()
        :return:
        """
        self.model().rescanCollections()

    def addCollection(self, collection, do_async=False):
        """
        shortcut to self.model().addCollection()
        :collection: collection to add
        :return:
        """
        if do_async:
            self.model().addCollectionAsync(collection)
        else:
            self.model().addCollection(collection)

    def removeCollection(self, collection):
        """
        shortcut to self.model().removeCollection()
        :collection: collection or collection name to remove
        :return: bool - if collection was removed
        """
        return self.model().removeCollection(collection)

    @Slot(str)
    def filterTable(self, filtername):
        super(CollectionWidget, self).filterTable(filtername)
        self.sort(0)

    def _addItem(self, collection):
        log('_addItem should be reimplemented in subclass to do what is needed in any specific situation', 3)

    # not raising cuz this is called deep through signal-slot mech, that cause exceptions to be f*cked somewhere on the way
    # raise NotImplementedError('This method should be overriden in subclasses to implement desired behaviour')

    def _itemInfo(self, index):
        log('_itemInfo should be reimplemented in subclass to do what is needed in any specific situation', 3)
        item = index.internalPointer()
        stuff = vars(item)
        for v in stuff:
            log(v + ' : ' + repr(stuff[v]), 2)

    def _renameItem(self, index):
        log('_renameItem should be reimplemented in subclass to do what is needed in any specific situation', 3)

    def _changeAccess(self, index):
        log('_changeAccess should be reimplemented in subclass to do what is needed in any specific situation', 3)

    def _replaceContent(self, index):
        log('_renameItem should be reimplemented in subclass to do what is needed in any specific situation', 3)

    def _confirmRemove(self, index):
        # reimplement this to add smth like confirmation window if needed
        return True

    def _removeIcon(self, index):
        """

        :param index:
        :return:
        """
        index.internalPointer().changeMetadata({'iconpixmap': None})

    def _uploadIcon(self, index):
        """
        :param index:
        :return:
        """
        if self.__openImageDialog is not None: return
        dialog = QFileDialog(self, "pick image file", QDir.homePath(), "Images (*.png *.xpm *.jpg *.jpeg *.bmp)")
        dialog.setFileMode(QFileDialog.ExistingFile)
        filename = None
        dialog.finished.connect(lambda res, obj=self, item=index.internalPointer(): obj._uploadIcon_iconSelected(res, item))
        self.__openImageDialog = dialog
        dialog.show()

    def _uploadIcon_iconSelected(self, result, item):
        self.__openImageDialog.deleteLater()
        sel = self.__openImageDialog.selectedFiles()
        self.__openImageDialog = None
        if not item.isValid(): return  # since dialog is not modal (QT bugs and crashes in case of modal) we should assume something might have happened to the item
        if result == 0: return
        filename = sel[0]
        pix = QPixmap()
        pix.load(filename)
        if pix.isNull():
            return  # bad pixmap. TODO: maybe give a warning or error
        pixsize = pix.size()
        if max(pixsize.width(), pixsize.height()) > 32:
            pix = pix.scaled(QSize(32, 32), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        if pix.isNull():
            return  # who knows
        item.changeMetadata({'iconpixmap': pix})  # TODO: BIG one - all changings to the items MUST somehow inform model so it changes display

    def __removeItem(self, index):  # TODO: why did i make it private with protected overridable confirm?
        if self._confirmRemove(index):
            self.model().removeRows(index.row(), 1, QModelIndex())

    def _itemContextMenu(self, index, sidemenu):
        item = index.internalPointer()
        newaction = sidemenu.addAction('info')
        newaction.triggered.connect(lambda checked=False, x=index: self._itemInfo(x))
        if not item.readonly():
            sidemenu.addSeparator()
            newaction = sidemenu.addAction('rename')
            newaction.triggered.connect(lambda checked=False, x=index: self._renameItem(x))
            newaction = sidemenu.addAction('change access')
            newaction.triggered.connect(lambda checked=False, x=index: self._changeAccess(x))
            newaction = sidemenu.addAction('replace content')
            newaction.triggered.connect(lambda checked=False, x=index: self._replaceContent(x))
            newaction = sidemenu.addAction('upload icon')
            newaction.triggered.connect(lambda checked=False, x=index: self._uploadIcon(x))
            newaction = sidemenu.addAction('remove icon')
            newaction.triggered.connect(lambda checked=False, obj=self, x=index: obj._removeIcon(x))
            # newaction.setEnabled(False)
            # TODO: automatically enable stuff if subclass overrides item methods!
            sidemenu.addSeparator()
            newaction = sidemenu.addAction('remove item')
            newaction.triggered.connect(lambda checked=False, x=index: self.__removeItem(x))

    ####Slots
    @Slot(QPoint)
    def showContextMenu(self, pos):
        menu = QMenu('orders, captain?', self)
        newaction = menu.addAction('choose this')
        newaction.triggered.connect(self.accept)

        sidemenu = menu.addMenu('collections')
        for col in self.model().collections():
            colmenu = sidemenu.addMenu(col.name())
            if col.readonly():
                newaction = colmenu.addAction('collection is READONLY')
                newaction.setEnabled(False)
            else:
                newaction = colmenu.addAction('add selected nodes')
                newaction.setData((col))
                newaction.triggered.connect(lambda checked=False, x=col: self._addItem(x))
        menu.addSeparator()

        if self.ui.mainView.currentIndex().isValid():
            cindex = self._mapToSource(self.ui.mainView.currentIndex())
            sidemenu = menu.addMenu('item')
            self._itemContextMenu(cindex, sidemenu)  # Allow subclasses to override submenu

        menu.popup(self.mapToGlobal(pos))
        menu.aboutToHide.connect(menu.deleteLater)
        return menu  # Slot does not need that, but if subclass overrides - it can modify default menu instead of creating one from ground up


####TESTING
if __name__ == '__main__':
    class FakeCollection(collectionbase.CollectionBase):
        def __init__(self):
            super(FakeCollection, self).__init__()
            self.__coll = [collectionbase.CollectionItem(self, 'item %s' % x, 'fat %s' % (x * 2), 'testnoid', x % 2, x % 4 < 2, metadata={'raw_url': 'https://fork', 'nettype': 'WOOF'}) for x in range(100)]

        def name(self):
            return 'testname'

        def list(self):
            return self.__coll

        def removeItem(self, item):
            self.__coll.remove(item)
            item.invalidate()


    import sys

    qapp = QApplication(sys.argv)

    col = FakeCollection()

    wid = CollectionWidget(metadataExposedKeys=('raw_url', 'nettype'))
    wid.move(800, 400)
    wid.addCollection(col)
    wid.accepted.connect(lambda x: log('dialog accepted "%s"' % x.name()))
    wid.finished.connect(lambda: qapp.quit())
    wid.show()
    sys.exit(qapp.exec_())
