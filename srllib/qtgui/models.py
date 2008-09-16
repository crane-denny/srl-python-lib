""" Collection of Qt model classes.
"""
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt

class _AppendRowCommand(QtGui.QUndoCommand):
    __super = QtGui.QUndoCommand

    def __init__(self, model, items, text, parent=None):
        if text is None:
            text = "append row"
        self.__super.__init__(self, text, parent)

        self.__model, self.__items = model, items

    def redo(self):
        # The model takes over ownership of items, so hand it copies
        # Also make sure to clone, since the object may be of an arbitrary
        # QStandardItem subclass
        self.__model.appendRow([item.clone() for item in self.__items])

    def undo(self):
        self.__model.removeRow(self.__model.rowCount()-1)

class _SetDataCommand(QtGui.QUndoCommand):
    def __init__(self, undo_model, model, index, role2value, parent=None,
            clear=False):
        assert not isinstance(model, int)
        QtGui.QUndoCommand.__init__(self, "set item data")
        (self.__undo_model, self.__model, self.__row, self.__col,
                self.__role2value, self.__parent, self.__clear) = (undo_model,
                        model, index.row(), index.column(), role2value,
                        index.parent(), clear)
        self.__prev = undo_model.itemData(undo_model.mapFromSource(index))

    def redo(self):
        idx = self.__get_index()
        if self.__clear:
            # This clears all roles
            self.__model.setItemData(idx, {})
        for role, value in self.__role2value.items():
            self.__model.setData(idx, value, role)

    def undo(self):
        self.__model.setItemData(self.__get_index(), self.__prev)

    def __get_index(self):
        return self.__model.index(self.__row, self.__col, self.__parent)

class _RemoveRowCommand(QtGui.QUndoCommand):
    def __init__(self, model, row, parent):
        QtGui.QUndoCommand.__init__(self)
        self.__model, self.__row, self.__parent = model, row, parent

    def redo(self):
        self.__items = self.__model.takeRow(self.__row)

    def undo(self):
        self.__model.insertRow(self.__row, self.__items)

class _TakeItemCommand(QtGui.QUndoCommand):
    def __init__(self, model, row, column, text):
        if text is None:
            text = "take item"
        QtGui.QUndoCommand.__init__(self, text)

        self.item = None
        self.__model, self.__row, self.__column = model, row, column

    def redo(self):
        self.item = self.__model.takeItem(self.__row, self.__column)

    def undo(self):
        self.__model.setItem(self.__row, self.__column, self.item)
        self.item = None # The item is taken over by the model, access unsafe

class UndoItemModel(QtGui.QSortFilterProxyModel):
    """ Item model that is capable of undoing operations.

    This model implements undo support on top of QStandardItemModel, through a
    proxy scheme.

    QSortFilterProxyModel is subclassed since this makes it simple to implement
    a proxy (with undo logic) for a standard item model, in fact it is
    recommended by the Qt documentation to base proxy implementations on this.
    @ivar undo_stack: The undo stack.
    """
    __super = QtGui.QSortFilterProxyModel

    def __init__(self, undo_stack=None, hor_headers=None, ver_headers=None,
        parent=None):
        """ Constructor.
        @ivar undo_stack: Optionally pass an undo stack to work with. If None,
        the model instantiates its own.
        @ivar hor_headers: Optionally specify horizontal header labels.
        @ivar ver_headers: Optionally specify vertical header labels.
        @ivar parent: Optionally pass QObject parent.
        """
        self.__super.__init__(self, parent)

        model = self.__model = QtGui.QStandardItemModel(self)
        self.setSourceModel(model)
        if undo_stack is None:
            undo_stack = QtGui.QUndoStack(self)
        self.undo_stack = undo_stack

        if hor_headers:
            model.setHorizontalHeaderLabels(hor_headers)
        if ver_headers:
            model.setVerticalHeaderLabels(ver_headers)

    def append_row(self, values, undo_text=None):
        """ Append row of values.

        Values may be represented as dicts, as a mapping from role to value.
        Otherwise values are taken to be for Qt.EditRole.
        @param undo_text: Optionally specify undo text.
        """
        items = []
        for val in values:
            item = QtGui.QStandardItem()
            if not isinstance(val, dict):
                val = {Qt.EditRole: val}
            for role, data in val.items():
                item.setData(QtCore.QVariant(data), role)
            items.append(item)
        self.undo_stack.push(_AppendRowCommand(self.__model, items,
            text=undo_text))

    #{ Implement model interface

    def setData(self, index, value, role=Qt.EditRole):
        role2value = {role: value}
        self.undo_stack.push(_SetDataCommand(self, self.__model,
            self.__model.index(index.row(), index.column()), role2value))
        return True

    def setItemData(self, index, roles, clear=False):
        self.undo_stack.push(_SetDataCommand(self, self.__model,
            self.__model.index(index.row(), index.column()), roles, clear=clear))
        return True

    #}

    #{ Expose QStandardItemModel methods

    def item(self, row, column=0):
        return self.__model.item(row, column)

    def setItem(self, *args):
        self.__model.setItem(*args)

    def takeItem(self, row, column=0, undo_text=None):
        cmd = _TakeItemCommand(self.__model, row, column, text=undo_text)
        self.undo_stack.push(cmd)
        return cmd.item
        # return self.__model.takeItem(row, column)

    def appendRow(self, items, undo_text=None):
        """ Append row of L{items<QtGui.QStandardItem>}.
        @param undo_text: Optionally specify undo text.
        """
        self.undo_stack.push(_AppendRowCommand(self.__model, items, text=
            undo_text))

    def removeRow(self, row, parent=QtCore.QModelIndex()):
        self.undo_stack.push(_RemoveRowCommand(self.__model, row, parent))

    def removeRows(self, row, count, parent=QtCore.QModelIndex(), undo_text=
        None):
        if undo_text is None:
            undo_text = "remove rows"
        self.undo_stack.beginMacro(undo_text)
        try:
            for i in reversed(range(row, row+count)):
                self.removeRow(i, parent)
        finally:
            self.undo_stack.endMacro()

    def setHorizontalHeaderLabels(self, labels):
        self.__model.setHorizontalHeaderLabels(labels)

    def setColumnCount(self, count):
        self.__model.setColumnCount(count)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return self.__model.columnCount()

    #}
