from PyQt4 import QtGui, QtCore

from testqtgui._common import *

import srllib.qtgui.widgets

class _FakeQLineEdit(guimock.QMock):
    _MockRealClass = QtGui.QLineEdit

    def __init__(self, contents, parent):
        guimock.QMock.__init__(self, returnValues={"text": contents})

class Blah(guimock.QMock):
    pass

class LineEditTest(QtTestCase):
    def test_construct_with_undo(self):
        """ Test constructing with undo. """
        stack = QtGui.QUndoStack()

        # Test default label for undo operation
        edit = self.__construct("Test", undo_stack=stack)
        edit.emit(QtCore.SIGNAL("textEdited(const QString&)"), "New")
        self.assertEqual(stack.undoText(), "edit text")

        # Test label for undo operation
        edit = self.__construct("Test", undo_stack=stack, undo_text=
            "editing test")
        edit.emit(QtCore.SIGNAL("textEdited(const QString&)"), "New")
        self.assertEqual(stack.undoText(), "editing test")

    def test_undo(self):
        """ Test undo functionality. """
        stack = QtGui.QUndoStack()
        edit = self.__construct("Initial", undo_stack=stack)
        edit.emit(QtCore.SIGNAL("textEdited(const QString&)"), "New")
        edit.emit(QtCore.SIGNAL("textEdited(const QString&)"), "New0")
        edit.emit(QtCore.SIGNAL("editingFinished()"))
        edit.emit(QtCore.SIGNAL("textEdited(const QString&)"), "New1")
        stack.undo()
        edit.mockCheckNamedCall(self, "setText", -1, "New0")
        stack.undo()
        edit.mockCheckNamedCall(self, "setText", -1, "Initial")
        stack.redo()
        edit.mockCheckNamedCall(self, "setText", -1, "New0")
        stack.redo()
        edit.mockCheckNamedCall(self, "setText", -1, "New1")

    def __construct(self, contents=QtCore.QString(), undo_stack=None,
        undo_text=None):
        self._set_attr(QtGui, "QLineEdit", _FakeQLineEdit)
        reload(srllib.qtgui.widgets)
        return srllib.qtgui.widgets.LineEdit(contents, undo_stack=undo_stack,
            undo_text=undo_text)
