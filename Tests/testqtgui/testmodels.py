from testqtgui._common import *

import srllib.qtgui.util
from srllib.qtgui import models

class UndoModelTest(QtTestCase):
    def test_setData(self):
        model = self.__construct(hor_headers=("1"))
        data = [QtCore.QVariant(x) for x in 1, 2]
        model.append_row([data[0]])

        stack = self.__undo_stack
        model.setData(model.index(0, 0), data[1])
        self.assertEqual(model.data(model.index(0, 0)), data[1])
        self.assertEqual(stack.undoText(), "set item data")
        stack.undo()
        self.assertEqual(model.data(model.index(0, 0)).toString(),
            data[0].toString())

    def __construct(self, hor_headers=None):
        self.__undo_stack = srllib.qtgui.util.UndoStack()
        return models.UndoItemModel(self.__undo_stack, hor_headers=hor_headers)
