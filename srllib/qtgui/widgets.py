""" Collection of widget classes. """
from PyQt4 import QtGui, QtCore

import srllib.qtgui

class _LineEditUndo(QtGui.QUndoCommand):
    __super = QtGui.QUndoCommand

    def __init__(self, edit, prev_text, cur_text, parent=None):
        self.__super.__init__(self, "Edit text", parent)
        self.__edit = edit
        self.__prev = prev_text
        self.__cur = cur_text

    def undo(self):
        self.__edit.setText(self.__prev)

    def redo(self):
        self.__edit.setText(self.__cur)

class LineEdit(QtGui.QLineEdit):
    """ Extension of QLineEdit.

    This class supports the Qt undo framework.
    """
    __super = QtGui.QLineEdit

    def __init__(self, contents=QtCore.QString(), parent=None, undo_stack=None):
        """ Constructor.

        @param undo_stack: Optionally specify an undo stack to manipulate as
        the line edit's text is edited.
        """
        self.__super.__init__(self, contents, parent)

        # Always cache the text as it is before the last change, for undo
        self.__cur_text = self.text()
        QtCore.QObject.connect(self, QtCore.SIGNAL("textEdited(const QString&"),
            self.__edited)
        srllib.qtgui.connect(self, "textEdited(const QString&)", self.__edited)
        self.__undo_stack = undo_stack

    def __edited(self, text):
        undo_stack = self.__undo_stack
        if undo_stack is None:
            return

        undo_stack.push(_LineEditUndo(self, self.__cur_text, text))
        self.__cur_text = text
