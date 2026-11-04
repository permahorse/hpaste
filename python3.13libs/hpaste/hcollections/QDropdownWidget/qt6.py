from PySide6.QtCore import Signal, Slot, QEvent, QRegularExpression, QSize, QSortFilterProxyModel, Qt
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QLayout, QLineEdit, QSizePolicy, QTableView, QVBoxLayout, QWidget

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
        if (parent := self.parent()) is not None:
            parent.accept()

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
        if self.parent() is not None and event.key() in (
                Qt.Key.Key_Up,
                Qt.Key.Key_Down,
                Qt.Key.Key_Return,
                Qt.Key.Key_Enter,
                Qt.Key.Key_Escape,
        ):
            # pass to parent. event.ignore() should do the same, but it's broken in h22
            self.parent().keyPressEvent(event)
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
        self.ui.mainLayout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self.ui.mainView = QAdjustedTableView()
        self.ui.mainView.horizontalHeader().hide()
        self.ui.mainView.verticalHeader().hide()

        self.ui.mainView.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.ui.mainView.setMinimumSize(128, 32)
        self.setMinimumSize(32, 32)

        self.ui.mainView.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self.ui.mainView.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.ui.mainView.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        # self.resize(128,512)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)

        self.__model = None
        self.__proxyModel = QSortFilterProxyModel(self)
        self.__proxyModel.setSourceModel(self.__model)
        self.__proxyModel.setFilterKeyColumn(0)
        self.__proxyModel.setFilterRegularExpression(QRegularExpression(".*", QRegularExpression.PatternOption.CaseInsensitiveOption))
        self.ui.mainView.setModel(self.__proxyModel)

        self.ui.nameInput = QFocusedLineEdit(self)
        self.ui.nameInput.setMinimumSize(32, 24)
        self.ui.nameInput.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)

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
        return True

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
        if event.key() == Qt.Key.Key_Up:
            cid = self.ui.mainView.currentIndex()
            if cid.row() > 0:
                self.ui.mainView.setCurrentIndex(self.__proxyModel.index(cid.row() - 1, cid.column()))
        elif event.key() == Qt.Key.Key_Down:
            cid = self.ui.mainView.currentIndex()
            if cid.row() < self.__proxyModel.rowCount() - 1:
                self.ui.mainView.setCurrentIndex(self.__proxyModel.index(cid.row() + 1, cid.column()))
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accept()
        elif event.key() == Qt.Key.Key_Escape:
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
