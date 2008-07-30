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
        """ Test undo support. """
        stack = QtGui.QUndoStack()
        edit = self.__construct("Initial", undo_stack=stack)
        edit.emit(QtCore.SIGNAL("textEdited(const QString&)"), "New")
        stack.undo()
        edit.mockCheckNamedCall(self, "setText", -1, "Initial")
        stack.redo()
        edit.mockCheckNamedCall(self, "setText", -1, "New")

    def __construct(self, contents=QtCore.QString(), undo_stack=None):
        self._set_attr(QtGui, "QLineEdit", _FakeQLineEdit)
        reload(srllib.qtgui.widgets)
        return srllib.qtgui.widgets.LineEdit(contents, undo_stack=undo_stack)
