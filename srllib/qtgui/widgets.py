""" Collection of widget classes.
"""
from PyQt4 import QtGui, QtCore

import srllib.qtgui

class _LineEditUndo(QtGui.QUndoCommand):
    __super = QtGui.QUndoCommand

    def __init__(self, edit, prev_text, cur_text, cmd_text, id_):
        self.__super.__init__(self, cmd_text, None)
        self.__edit = edit
        self.__prev = prev_text
        self.__cur = cur_text
        self.__id = id_

    def id(self):
        return self.__id

    def mergeWith(self, other):
        if not isinstance(other, _LineEditUndo) or other.id() != self.id():
            return False

        self.__cur = other.__cur
        return True

    def undo(self):
        self.__edit.setText(self.__prev)

    def redo(self):
        self.__edit.setText(self.__cur)

class LineEdit(QtGui.QLineEdit):
    """ Extension of QLineEdit.

    This class supports the Qt undo framework. An undo operation spans the
    interval from the user starts entering text until the widget either loses
    focus or Enter is pressed, this is considered a suitable granularity for
    this kind of widget.
    """
    __super = QtGui.QLineEdit

    def __init__(self, contents=QtCore.QString(), parent=None, undo_stack=None,
        undo_text=None):
        """ Constructor.

        @param undo_stack: Optionally specify an undo stack to manipulate as
        the line edit's text is edited.
        @param undo_text: Optionally specify descriptive text for the undo/redo
        operation.
        """
        self.__super.__init__(self, contents, parent)

        # Always cache the text as it is before the last change, for undo
        self.__cur_text = self.text()
        srllib.qtgui.connect(self, "textEdited(const QString&)", self.__edited)
        srllib.qtgui.connect(self, "editingFinished()", self.__editing_finished)
        self.__undo_stack = undo_stack
        if undo_text is None:
            undo_text = "edit text"
        self.__undo_txt = undo_text
        self.__cur_editing = None

    def setText(self, text, undoable=False):
        if undoable:
            self.__edited(text)
        self.__super.setText(self, text)
        self.__cur_text = text

    def __edited(self, text):
        undo_stack = self.__undo_stack
        if undo_stack is None:
            return

        if self.__cur_editing != undo_stack.index()-1:
            # We're starting a new operation
            id_ = self.__cur_editing = undo_stack.index()
        else:
            id_ = self.__cur_editing

        # Make sure to make a copy of the text
        my_text = QtCore.QString(text)
        undo_stack.push(_LineEditUndo(self, self.__cur_text, my_text,
            self.__undo_txt, id_))
        self.__cur_text = my_text

    def __editing_finished(self):
        """ We've either lost focus or the user has pressed Enter.
        """
        undo_stack = self.__undo_stack
        if undo_stack is None:
            return

        self.__cur_editing = None
