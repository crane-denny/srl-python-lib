""" Collection of widget classes.
"""
from PyQt4 import QtGui, QtCore

import srllib.qtgui

class _LineEditUndo(QtGui.QUndoCommand):
    __super = QtGui.QUndoCommand

    def __init__(self, edit, prev_text, cur_text, label):
        self.__super.__init__(self, label, None)
        self.__edit = edit
        self.__prev = prev_text
        self.__cur = cur_text

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
        QtCore.QObject.connect(self, QtCore.SIGNAL("textEdited(const QString&"),
            self.__edited)
        QtCore.QObject.connect(self, QtCore.SIGNAL("editingFinished()"),
            self.__editing_finished)
        self.__undo_stack = undo_stack
        if undo_text is None:
            undo_text = "edit text"
        self.__undo_txt = undo_text

        self.__cur_undo = None

    def __edited(self, text):
        print "Edited"
        undo_stack = self.__undo_stack
        if undo_stack is None:
            return

        if self.__cur_undo is None:
            # We're
            pass

        # Make sure to make a copy of the text
        my_text = QtCore.QString(text)
        undo_stack.push(_LineEditUndo(self, self.__cur_text, my_text,
            self.__undo_txt))
        self.__cur_text = my_text

    def __editing_finished(self):
        """ We've either lost focus or the user has pressed Enter.
        """
        undo_stack = self.__undo_stack
        if undo_stack is None:
            return


