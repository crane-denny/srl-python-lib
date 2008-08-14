from testqtgui._common import *

import srllib.qtgui.util
from srllib.qtgui import models

class UndoModelTest(QtTestCase):
    def test_construct(self):
        model = self.__construct()
        self.assertIs(model.undo_stack, self.__undo_stack)

    def test_setData(self):
        data = [QtCore.QVariant(x) for x in 1, 2]
        model = self.__construct(hor_headers=("1"), initial_rows=[[data[0]]])
        stack = self.__undo_stack

        model.setData(model.index(0, 0), data[1])
        self.assertEqual(model.data(model.index(0, 0)), data[1])
        self.assertEqual(stack.undoText(), "set item data")
        self.assertEqual(stack.count(), 1)
        stack.undo()
        self.assertEqual(model.data(model.index(0, 0)).toString(),
            data[0].toString())

    def test_setItemData(self):
        def check_data(model, row, column, data):
            for role in (Qt.EditRole, Qt.UserRole):
                self.assertEqual(model.data(model.index(row, column),
                    role).toString(), data[role].toString())

        data = [{}, {}]
        for role in (Qt.EditRole, Qt.UserRole):
            data[0][role] = QtCore.QVariant(0)
            data[1][role] = QtCore.QVariant(1)
        model = self.__construct(hor_headers=("1"), initial_rows=[[data[0]]])
        stack = self.__undo_stack

        model.setItemData(model.index(0, 0), data[1])
        check_data(model, 0, 0, data[1])
        self.assertEqual(stack.undoText(), "set item data")
        self.assertEqual(stack.count(), 1)
        stack.undo()
        check_data(model, 0, 0, data[0])

    def test_appendRow(self):
        class MyItem(QtGui.QStandardItem):
            def clone(self):
                """ Necessary when adding to model. """
                return MyItem(self)

        model = self.__construct(["1"])
        stack = self.__undo_stack

        item = MyItem("text")
        model.appendRow([item])
        self.assertIsNot(model.item(0), item)
        self.assert_(isinstance(model.item(0), MyItem))
        self.assertEqual(stack.count(), 1)
        self.assertEqual(stack.undoText(), "append row")
        stack.undo()
        self.assertEqual(model.rowCount(), 0)
        stack.redo()
        self.assertEqual(model.data(model.index(0, 0)).toString(), "text")
        stack.undo()

        model.appendRow([MyItem("text")], undo_text="add table row")
        self.assertEqual(stack.undoText(), "add table row")

    def test_takeItem(self):
        model = self.__construct(initial_rows=[["text"]])
        stack = self.__undo_stack

        item = model.takeItem(0)
        self.assertEqual(item.text(), "text")
        self.assertIs(model.item(0), None)
        self.assertEqual(stack.count(), 1)
        self.assertEqual(stack.undoText(), "take item")
        stack.undo()
        stack.redo()
        stack.undo()
        self.assertEqual(model.item(0).text(), "text")
        # Now with undo text
        item = model.takeItem(0, undo_text="delete cell")
        self.assertEqual(stack.undoText(), "delete cell")

    def test_setItem(self):
        model = self.__construct(initial_rows=[["old text", "old text"]])
        model.setItem(0, 1, QtGui.QStandardItem("new text"))
        self.assertEqual(model.item(0, 1).text(), "new text")
        self.assertEqual(self.__undo_stack.count(), 0)

    def __construct(self, hor_headers=None, initial_rows=None):
        stack = self.__undo_stack = srllib.qtgui.util.UndoStack()
        model = models.UndoItemModel(self.__undo_stack, hor_headers=hor_headers)
        if initial_rows:
            stack.is_enabled = False
            for row in initial_rows:
                model.append_row(row)
            stack.is_enabled = True
        return model
