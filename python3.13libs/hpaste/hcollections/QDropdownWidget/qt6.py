try:
    from PySide6.QtCore import *
    from PySide6.QtWidgets import *
    from PySide6.QtGui import *
except ImportError:
    from PySide2.QtCore import *
    from PySide2.QtWidgets import *
    from PySide2.QtGui import *

import re


class QAdjustedTableView(QTableView):
    itemsChanged = Signal()

    def __init__(self, parent=None):
        super(QAdjustedTableView, self).__init__(parent)

        self.verticalHeader().sectionCountChanged.connect(self.headersChanged)
        self.verticalHeader().sectionCountChanged.connect(self.headersChanged)

    def headersChanged(self):
        self.updateGeometry()
        self.itemsChanged.emit()

    def mouseDoubleClickEvent(self, event):
        event.accept()
        if self.parent() is not None:
            self.parent().accept()

    # ### QT
    def sizeHint(self):
        wgt = 0
        if self.model():
            for i in range(self.horizontalHeader().count()):
                if self.horizontalHeader().isSectionHidden(i): continue
                wgt += self.sizeHintForColumn(i) + 2  # CAUTION: there's no confirmation that header logical index corresponds directly to View's columns

        scrbarw = self.verticalScrollBar().sizeHint().width()
        return QSize(wgt + scrbarw + 8, self.verticalHeader().length() + 4)


class QFocusedLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super(QFocusedLineEdit, self).__init__(parent)

    def focusOutEvent(self, event):
        self.setFocus()
        event.accept()

    def keyPressEvent(self, event):
        if self.parent() is not None and event.key() == Qt.Key_Up or event.key() == Qt.Key_Down:
            event.ignore()  # let it be processed by parent
        else:
            super(QFocusedLineEdit, self).keyPressEvent(event)


class UiHolder(object):
    pass


class QDropdownWidget(QWidget):
    accepted = Signal(object)
    finished = Signal()

    def __init__(self, parent=None):
        super(QDropdownWidget, self).__init__(parent)
        self.__filterList = []

        self.ui = UiHolder()
        self.ui.mainLayout = QVBoxLayout(self)
        self.ui.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.ui.mainLayout.setSpacing(2)
        self.ui.mainLayout.setSizeConstraint(QLayout.SetMinimumSize)
        self.ui.mainView = QAdjustedTableView(self)
        self.ui.mainView.horizontalHeader().hide()
        self.ui.mainView.verticalHeader().hide()

        try:  # qt5
            self.ui.mainView.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        except:  # qt4
            self.ui.mainView.horizontalHeader().setResizeMode(QHeaderView.Stretch)

        self.ui.mainView.setMinimumSize(128, 32)
        self.setMinimumSize(32, 32)

        self.ui.mainView.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.ui.mainView.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ui.mainView.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        # self.resize(128,512)
        self.setWindowFlags(Qt.Popup)

        self.__model = None
        self.__proxyModel = QSortFilterProxyModel(self)
        self.__proxyModel.setSourceModel(self.__model)
        self.__proxyModel.setFilterKeyColumn(0)
        self.__proxyModel.setFilterRegularExpression(QRegularExpression(".*", QRegularExpression.PatternOption.CaseInsensitiveOption))
        self.ui.mainView.setModel(self.__proxyModel)

        self.ui.nameInput = QFocusedLineEdit(self)
        self.ui.nameInput.setMinimumSize(32, 24)
        self.ui.nameInput.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)

        self.ui.mainLayout.addWidget(self.ui.nameInput)
        self.ui.mainLayout.addWidget(self.ui.mainView)

        # SIGNALS
        self.ui.mainView.itemsChanged.connect(self.resizeToTable)
        self.ui.nameInput.textChanged.connect(self.filterTable)

        # FINAL TOUCH
        self.setFocusProxy(self.ui.nameInput)
        self.ui.nameInput.setFocus()

    def appendFilter(self, filter):
        assert isinstance(filter, QSortFilterProxyModel), 'filter must be a QSortFilterProxyModel instance'
        if filter in self.__filterList:
            return False
        if len(self.__filterList) == 0:
            filter.setSourceModel(self.__model)
        else:
            filter.setSourceModel(self.__filterList[-1])
        self.__proxyModel.setSourceModel(filter)

        self.__filterList.append(filter)

    # Todo: implement insertFilter or smth

    def removeFilter(self, filter_or_id):
        assert isinstance(filter_or_id, QSortFilterProxyModel) or isinstance(filter_or_id, int), 'filter_or_id should be either an instance of QSortFilterProxyModel or an int'
        id = -1
        if isinstance(filter_or_id, QSortFilterProxyModel):
            filter = filter_or_id
            if filter not in self.__filterList:
                return False
            id = self.__filterList.index(filter)
        else:
            id = filter_or_id

        lf = len(self.__filterList)
        if id < -lf or id >= lf:
            raise ValueError('id is off the bounds')
        if id < 0:
            id += lf  # easier to keep id non negative
        if id == 0:
            if lf > 1:
                self.__filterList[1].setSourceModel(self.__model)
            else:
                self.__proxyModel.setSourceModel(self.__model)
        elif id == lf - 1:  # also since id!=0 means lf is >1
            self.__proxyModel.setSourceModel(self.__filterList[id - 1])
        else:  # so id!=0 and id!=lf-1
            self.__filterList[id + 1].setSourceModel(self.__filterList[id - 1])

        self.__filterList[id].setModel(None)
        del self.__filterList[id]
        return True

    def _mapToSource(self, index):
        retindex = self.__proxyModel.mapToSource(index)
        for filter in reversed(self.__filterList):
            retindex = filter.mapToSource(retindex)
        return retindex

    def _mapFromSource(self, index):
        retindex = index
        for filter in self.__filterList:
            retindex = filter.mapFromSource(retindex)
        return self.__proxyModel.mapFromSource(retindex)

    def model(self):
        return self.__model

    def setModel(self, model):
        self.__model = model
        if len(self.__filterList) > 0:
            self.__filterList[0].setSourceModel(self.__model)
        else:
            self.__proxyModel.setSourceModel(self.__model)

    # def _proxyModel(self):
    #    return self.__proxyModel

    @Slot()
    def resizeToTable(self):

        # hgt=self.ui.mainView.verticalHeader().length()
        # self.resize(self.size().width(),hgt+32)
        self.adjustSize()
        if self.__model is not None:
            self.ui.mainView.setCurrentIndex(self.__proxyModel.index(0, 0))

    @Slot(str)
    def filterTable(self, filtername):
        self.__proxyModel.setFilterRegularExpression(QRegularExpression(".+".join(re.split(r'\s+', filtername)), QRegularExpression.PatternOption.CaseInsensitiveOption))

    @Slot(int)
    def sort(self, column=0):
        self.__proxyModel.sort(column, Qt.AscendingOrder)

    ####QT overrides
    def changeEvent(self, event):
        super(QDropdownWidget, self).changeEvent(event)
        if self.isVisible() and event.type() == QEvent.ActivationChange and not self.isActiveWindow():
            self.hide()
            event.accept()

    @Slot()
    def accept(self):
        self.hide()
        self.accepted.emit(self._mapToSource(self.ui.mainView.currentIndex()).internalPointer())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up:
            cid = self.ui.mainView.currentIndex()
            if cid.row() > 0:
                self.ui.mainView.setCurrentIndex(self.__proxyModel.index(cid.row() - 1, cid.column()))
        elif event.key() == Qt.Key_Down:
            cid = self.ui.mainView.currentIndex()
            if cid.row() < self.__proxyModel.rowCount() - 1:
                self.ui.mainView.setCurrentIndex(self.__proxyModel.index(cid.row() + 1, cid.column()))
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.accept()
        elif event.key() == Qt.Key_Escape:
            self.hide()
        event.accept()

    def showEvent(self, event):
        self.ui.nameInput.setText('')
        self.ui.mainView.setCurrentIndex(self.__proxyModel.index(0, 0))
        # screen = QGuiApplication.screenAt(self.pos()) #  proper way, but only available in qt5 and for some reason missing in PySide2
        screenGeo = self.screen().geometry()

        maxsizeY = screenGeo.height() - self.pos().y()
        self.setMaximumHeight(max(self.minimumHeight(), maxsizeY))
        self.ui.mainView.resizeColumnsToContents()
        self.adjustSize()
        self.ui.mainView.verticalScrollBar().setValue(0)
        event.accept()

    def hideEvent(self, event):
        self.finished.emit()
