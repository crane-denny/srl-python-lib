"""Test util module."""
from _common import *
if has_qt4:
    from testqtgui._common import *

    from srllib.qtgui import util

if has_qt4:
    class _TestCommand(QtGui.QUndoCommand):
        def __init__(self):
            QtGui.QUndoCommand.__init__(self)
            self.done = False

        def redo(self):
            self.done = True

        def undo(self):
            pass

@only_qt4
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

@only_qt4
class VariousTest(QtTestCase):
    def test_Action(self):
        """ Test Action factory. """
        def slot():
            self.__called = True
        self._set_attr(QtGui, "QAction", mock.MockFactory(guimocks.QActionMock))
        self._set_attr(QtGui, "QIcon", mock.MockFactory(guimocks.QIconMock))
        self.__called = False

        action = util.Action("action", slot, "icon", "ctrl+s", None)
        icon = guimocks.QIconMock.mockGetAllInstances()[0]
        self.assertEqual(action.mockConstructorArgs, (icon, "action", None))
        action.mockCheckNamedCall(self, "setShortcut", 0, "ctrl+s")
        action.trigger()
        self.assert_(self.__called)


if has_qt4:
    class _BrowseFile(util._BrowseHelper, guimocks.QWidgetMock):
        def __init__(self, *args, **kwds):
            guimocks.QWidgetMock.__init__(self)
            self.path_edit = guimocks.QLineEditMock()
            util._BrowseHelper.__init__(self, *args, **kwds)


@only_qt4
class BrowseHelperTest(QtTestCase):
    def test_construct(self):
        browse = self.__test_construct()
        self.assertNot(browse.path_edit.isReadOnly())
        browse = self.__test_construct(kwds={"readonly": True})
        self.assert_(browse.path_edit.isReadOnly())
        browse = self.__test_construct(kwds={"path": "file"})

    def __test_construct(self, kwds={}):
        browse = self.__construct(kwds=kwds)
        path = kwds.get("path")

        path_edit = browse.path_edit
        if path is not None:
            self.assertEqual(path_edit.text(), path)
        else:
            self.assertEqual(path_edit.text(), "")
        tooltip = kwds.get("tooltip")
        if tooltip is not None:
            path_edit.mockCheckNamedCall(self, "setToolTip", -1, tooltip)
        return browse

    def __construct(self, kwds={}):
        browser = _BrowseFile(**kwds)
        return browser
