from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt

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

    def test_undo_setText_undoable(self):
        """ Test undo in conjunction with setText, with undoable=True. """
        edit, stack = self.__construct("Old", undo=True)
        edit.setText("New", undoable=True)
        stack.undo()
        edit.mockCheckNamedCall(self, "setText", -1, "Old")

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

class NumericalLineEditTest(QtTestCase):
    def test_construct(self):
        edit = self.__construct(True)
        call = edit.mockGetNamedCall("setValidator", 0)
        self.assert_(isinstance(call.args[0], QtGui.QDoubleValidator))
        edit = self.__construct(True, minimum=0, maximum=1)
        call = edit.mockGetNamedCall("setValidator", 0)
        vtor = call.args[0]
        self.assert_(isinstance(vtor, QtGui.QDoubleValidator))
        self.assertEqual(vtor.bottom(), 0)
        self.assertEqual(vtor.top(), maximum)

        edit = self.__construct(False)
        call = edit.mockGetNamedCall("setValidator", 0)
        self.assert_(isinstance(call.args[0], QtGui.QIntValidator))
        edit = self.__construct(True, minimum=0, maximum=1)
        call = edit.mockGetNamedCall("setValidator", 0)
        vtor = call.args[0]
        self.assert_(isinstance(vtor, QtGui.QIntValidator))
        self.assertEqual(vtor.bottom(), 0)
        self.assertEqual(vtor.top(), maximum)
        self.assertRaises(ValueError, self.__construct, False, minimum=0.1)
        self.assertRaises(ValueError, self.__construct, False, maximum=0.1)

    def __construct(self, floating_point, contents=QtCore.QString(),
        minimum=None, maximum=None):
        self._set_attr(QtGui, "QLineEdit", _FakeQLineEdit)
        reload(srllib.qtgui.widgets)
        edit = srllib.qtgui.widgets.NumericalLineEdit(floating_point=
                floating_point, contents=contents, minimum=minimum, maximum=
                maximum)
        return edit

class _FakeQCheckBox(guimock.QMock):
    _MockRealClass = QtGui.QCheckBox

    def __init__(self, label, parent):
        guimock.QMock.__init__(self, returnValues={"checkState": Qt.Unchecked})

    def setCheckState(self, checkState):
        # PyQt doesn't accept integers for state ..
        assert isinstance(checkState, Qt.CheckState)
        self.mockSetReturnValue("checkState", checkState)
        self.emit(QtCore.SIGNAL("stateChanged(int)"), int(checkState))

class CheckBoxTest(QtTestCase):
    def test_construct_with_undo(self):
        """ Test constructing with undo. """
        # Test default label for undo operation
        checkbox, stack = self.__construct(undo=True)
        self.__change_state(checkbox, True)
        self.assertEqual(stack.undoText(), "")

        # Test label for undo operation
        checkbox, stack = self.__construct(undo=True, undo_text=
            "check test")
        self.__change_state(checkbox, True)
        self.assertEqual(stack.undoText(), "check test")

    def test_undo(self):
        """ Test undo functionality. """
        checkbox, stack = self.__construct(undo=True)
        self.__change_state(checkbox, True)
        self.__change_state(checkbox, False)
        stack.undo()
        checkbox.mockCheckNamedCall(self, "setCheckState", -1, Qt.Checked)
        stack.undo()
        checkbox.mockCheckNamedCall(self, "setCheckState", -1, Qt.Unchecked)
        stack.redo()
        checkbox.mockCheckNamedCall(self, "setCheckState", -1, Qt.Checked)

    def __change_state(self, checkbox, checked):
        if checked:
            state = int(Qt.Checked)
        else:
            state = int(Qt.Unchecked)
        checkbox.emit(QtCore.SIGNAL("stateChanged(int)"), state)

    def __construct(self, checked=False, undo=False, undo_text=None):
        if undo:
            undo_stack = QtGui.QUndoStack()
        self._set_attr(QtGui, "QCheckBox", _FakeQCheckBox)
        reload(srllib.qtgui.widgets)
        checkbox = srllib.qtgui.widgets.CheckBox(undo_stack=undo_stack,
            undo_text=undo_text)
        if not undo:
            return checkbox
        return checkbox, undo_stack
