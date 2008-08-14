from testqtgui._common import *

import srllib.qtgui.util
from srllib.qtgui import models

class UndoModelTest(QtTestCase):
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
            pass

        model = self.__construct(["1"])
        stack = self.__undo_stack

        model.appendRow([MyItem("text")])
        self.assertEqual(stack.count(), 1)
        self.assertEqual(stack.undoText(), "append row")
        stack.undo()
        self.assertEqual(model.rowCount(), 0)
        stack.redo()
        self.assertEqual(model.data(model.index(0, 0)).toString(), "text")
        stack.undo()

        model.appendRow([MyItem("text")], undo_text="add table row")
        self.assertEqual(stack.undoText(), "add table row")

    def __construct(self, hor_headers=None, initial_rows=None):
        stack = self.__undo_stack = srllib.qtgui.util.UndoStack()
        model = models.UndoItemModel(self.__undo_stack, hor_headers=hor_headers)
        if initial_rows:
            stack.is_enabled = False
            for row in initial_rows:
                model.append_row(row)
            stack.is_enabled = True
        return model
