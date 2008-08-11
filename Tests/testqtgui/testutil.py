""" Test util module. """
from testqtgui._common import *

from srllib.qtgui import util

class _TestCommand(QtGui.QUndoCommand):
    def __init__(self):
        QtGui.QUndoCommand.__init__(self)
        self.done = False

    def redo(self):
        self.done = True

    def undo(self):
        pass

class UndoStackTest(TestCase):
    def test_construct(self):
        stack = util.UndoStack()
        self.assert_(stack.is_enabled)

    def test_construct_disabled(self):
        stack = util.UndoStack(enable=False)
        self.assertNot(stack.is_enabled)

    def test_push(self):
        stack = util.UndoStack()
        cmd = _TestCommand()
        stack.push(cmd)
        self.assert_(cmd.done)

    def test_disable(self):
        """ Test disabling stack. """
        stack = util.UndoStack()
        stack.is_enabled = False
        self.__test_push(stack)

    def test_enable(self):
        """ Test enabling stack. """
        stack = util.UndoStack(enable=False)
        stack.is_enabled = True
        self.__test_push(stack)

    def __test_push(self, stack):
        count = stack.count()
        cmd = _TestCommand()
        stack.push(cmd)
        self.assert_(cmd.done)
        if stack.is_enabled:
            self.assertEqual(stack.count(), count+1)
        else:
            self.assertEqual(stack.count(), count)
