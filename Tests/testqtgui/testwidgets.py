from PyQt4 import QtGui, QtCore

from testqtgui._common import *

import srllib.qtgui.widgets

class _FakeQLineEdit(guimock.QMock):
    _MockRealClass = QtGui.QLineEdit

    def __init__(self, contents, parent):
        guimock.QMock.__init__(self, returnValues={"text": contents})

    def setText(self, text):
        self.mockSetReturnValue("text", text)

class LineEditTest(QtTestCase):
    def test_construct_with_undo(self):
        """ Test constructing with undo. """
        # Test default label for undo operation
        edit, stack = self.__construct("Test", undo=True)
        edit.emit(QtCore.SIGNAL("textEdited(const QString&)"), "New")
        self.assertEqual(stack.undoText(), "edit text")

        # Test label for undo operation
        edit, stack = self.__construct("Test", undo=True, undo_text=
            "editing test")
        edit.emit(QtCore.SIGNAL("textEdited(const QString&)"), "New")
        self.assertEqual(stack.undoText(), "editing test")

    def test_undo(self):
        """ Test undo functionality. """
        edit, stack = self.__construct("Initial", undo=True)
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
        stack.undo()
        edit.mockCheckNamedCall(self, "setText", -1, "New0")

    def test_undo_setText(self):
        """ Test undo in conjunction with setText. """
        edit, stack = self.__construct(undo=True)
        edit.setText("Test")
        self.assertNot(stack.canUndo())
        edit.emit(QtCore.SIGNAL("textEdited(const QString&)"), "New")
        stack.undo()
        edit.mockCheckNamedCall(self, "setText", -1, "Test")

    def __construct(self, contents=QtCore.QString(), undo=False,
        undo_text=None):
        if undo:
            undo_stack = QtGui.QUndoStack()
        self._set_attr(QtGui, "QLineEdit", _FakeQLineEdit)
        reload(srllib.qtgui.widgets)
        edit = srllib.qtgui.widgets.LineEdit(contents, undo_stack=undo_stack,
            undo_text=undo_text)
        if not undo:
            return edit
        return edit, undo_stack
