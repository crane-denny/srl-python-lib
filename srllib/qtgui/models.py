""" Collection of Qt model classes.
"""
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt
import copy

class _AppendRowCommand(QtGui.QUndoCommand):
    __super = QtGui.QUndoCommand

    def __init__(self, model, items, parent=None):
        self.__super.__init__(self, parent)

        self.__model, self.__items = model, items

    def redo(self):
        # The model takes over ownership of items, so hand it copies
        self.__model.appendRow([QtGui.QStandardItem(item) for item in
            self.__items])

    def undo(self):
        self.__model.removeRow(self.__model.rowCount()-1)

class _SetDataCommand(QtGui.QUndoCommand):
    def __init__(self, model, index, value, role, parent=None):
        QtGui.QUndoCommand.__init__(self)
        (self.__model, self.__row, self.__col, self.__parent, self.__value,
            self.__role) = (model, index.row(), index.column(),
                index.parent(), value, role)
        self.__prev = self.__model.data(index, self.__role)

    def redo(self):
        self.__model.setData(self.__get_index(), self.__value, self.__role)

    def undo(self):
        self.__model.setData(self.__get_index(), self.__prev, self.__role)

    def __get_index(self):
        return self.__model.index(self.__row, self.__col, self.__parent)

class _RemoveRowCommand(QtGui.QUndoCommand):
    def __init__(self, model, row):
        QtGui.QUndoCommand.__init__(self)
        self.__model, self.__row = model, row

    def redo(self):
        self.__items = self.__model.takeRow(self.__row)

    def undo(self):
        self.__model.insertRow(self.__row, self.__items)

class UndoItemModel(QtGui.QSortFilterProxyModel):
    """ Item model that is capable of undoing operations.

    This model implements undo support on top of QStandardItemModel, through a
    proxy scheme.

    QSortFilterProxyModel is subclassed since this makes it simple to implement
    a proxy (with undo logic) for a standard item model, in fact it is
    recommended by the Qt documentation to base proxy implementations on this.
    """
    __super = QtGui.QSortFilterProxyModel

    def __init__(self, undo_stack, hor_headers=None, ver_headers=None,
        parent=None):
        assert undo_stack is not None
        self.__super.__init__(self, parent)
        model = self.__model = QtGui.QStandardItemModel(self)
        self.setSourceModel(model)

        self.__undo_stack = undo_stack

        if hor_headers:
            model.setHorizontalHeaderLabels(hor_headers)
        if ver_headers:
            model.setVerticalHeaderLabels(ver_headers)

    def append_row(self, values):
        """ Append row of values.

        Values may be represented as dicts, as a mapping from role to value.
        Otherwise values are taken to be for Qt.EditRole.
        """
        items = []
        for val in values:
            item = QtGui.QStandardItem()
            if not isinstance(val, dict):
                val = {Qt.EditRole: val}
            for role, data in val.items():
                item.setData(QtCore.QVariant(data), role)
            items.append(item)
        self.__undo_stack.push(_AppendRowCommand(self.__model, items))

    #{ Implement model interface

    def setData(self, index, value, role=Qt.EditRole):
        self.__undo_stack.push(_SetDataCommand(self.__model, index, value,
            role))
        return True

    #}

    #{ Expose QStandardItemModel methods

    def item(self, row, column=0):
        return self.__model.item(row, column)

    def appendRow(self, items):
        """ Append row of L{items<QtGui.QStandardItem>}.
        """
        self.__undo_stack.push(_AppendRowCommand(self.__model, items))

    def removeRow(self, row, parent=QtCore.QModelIndex()):
        self.__undo_stack.push(_RemoveRowCommand(self.__model, row, parent))

    def setHorizontalHeaderLabels(self, labels):
        self.__model.setHorizontalHeaderLabels(labels)

    def setColumnCount(self, count):
        self.__model.setColumnCount(count)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return self.__model.columnCount()

    #}
