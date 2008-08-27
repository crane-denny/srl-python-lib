""" Collection of widget classes.
"""
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt

import srllib.qtgui

class _LineEditUndo(QtGui.QUndoCommand):
    __super = QtGui.QUndoCommand

    def __init__(self, edit, prev_text, cur_text, cmd_text, id_):
        self.__super.__init__(self, cmd_text)
        self.__edit = edit
        self.__prev = prev_text
        self.__cur = cur_text
        self.__id = id_

    def id(self):
        return self.__id

    def mergeWith(self, other):
        if not isinstance(other, _LineEditUndo) or other.id() != self.id():
            return False

        self.__cur = other.__cur
        return True

    def undo(self):
        self.__edit.setText(self.__prev)

    def redo(self):
        self.__edit.setText(self.__cur)

class _LineEditHelper(object):
    def __init__(self, undo_stack, undo_text):
        # Always cache the text as it is before the last change, for undo
        self.__cur_text = self.text()
        srllib.qtgui.connect(self, "textEdited(const QString&)", self.__edited)
        srllib.qtgui.connect(self, "editingFinished()", self.__editing_finished)
        self.__undo_stack = undo_stack
        if undo_text is None:
            undo_text = "edit text"
        self.__undo_txt = undo_text
        self.__cur_editing = None

    def setText(self, text, undoable=False):
        if undoable:
            self.__edited(text)
        self._qbase.setText(self, text)
        self.__cur_text = text

    def __edited(self, text):
        """ React to text being changed. """
        undo_stack = self.__undo_stack
        if undo_stack is None:
            return

        if self.__cur_editing != undo_stack.index()-1:
            # We're starting a new operation
            id_ = self.__cur_editing = undo_stack.index()
        else:
            id_ = self.__cur_editing

        # Make sure to make a copy of the text
        my_text = QtCore.QString(text)
        undo_stack.push(_LineEditUndo(self, self.__cur_text, my_text,
            self.__undo_txt, id_))
        self.__cur_text = my_text

    def __editing_finished(self):
        """ We've either lost focus or the user has pressed Enter.
        """
        undo_stack = self.__undo_stack
        if undo_stack is None:
            return

        self.__cur_editing = None

class LineEdit(_LineEditHelper, QtGui.QLineEdit):
    """ Extension of QLineEdit.

    This class supports the Qt undo framework. An undo operation spans the
    interval from the user starts entering text until the widget either loses
    focus or Enter is pressed, this is considered a suitable granularity for
    this kind of widget.
    """
    _qbase = QtGui.QLineEdit

    def __init__(self, contents=QtCore.QString(), parent=None, undo_stack=None,
        undo_text=None):
        """ Constructor.

        @param undo_stack: Optionally specify an undo stack to manipulate as
        the line edit's text is edited.
        @param undo_text: Optionally specify descriptive text for the undo/redo
        operation.
        """
        self._qbase.__init__(self, contents, parent)
        _LineEditHelper.__init__(self, undo_stack, undo_text)

class _NumericalLineEditHelper(object):
    def __init__(self, floating_point, minimum, maximum):
        if floating_point:
            vtor = QtGui.QDoubleValidator(self)
            self.setValidator(vtor)
            if minimum is not None:
                vtor.setBottom(minimum)
            if maximum is not None:
                vtor.setTop(maximum)
        else:
            vtor = QtGui.QIntValidator(self)
            self.setValidator(vtor)
            if minimum is not None:
                if not isinstance(minimum, int):
                    raise ValueError(minimum)
                vtor.setBottom(minimum)
            if maximum is not None:
                if not isinstance(maximum, int):
                    raise ValueError(maximum)
                vtor.setTop(maximum)

class NumericalLineEdit(LineEdit):
    """ Line edit specialization that only accepts numeric input. """
    _qbase = LineEdit

    def __init__(self, floating_point=True, contents=QtCore.QString(),
            minimum=None, maximum=None, parent=None, undo_stack=None,
            undo_text=None):
        """ Constructor.
        @param floating_point: Accept floating point numbers, not just integers?
        @param minimum: Optionally specify minimum acceptable value.
        @param maximum: Optionally specify maximum acceptable value.
        """
        self._qbase.__init__(self, contents, parent, undo_stack, undo_text)
        _NumericalLineEditHelper.__init__(self, floating_point, minimum,
            maximum)

class _CheckBoxUndo(QtGui.QUndoCommand):
    __super = QtGui.QUndoCommand

    def __init__(self, checkbox, prev_state, new_state, cmd_text):
        self.__super.__init__(self, cmd_text)
        self.__checkbox = checkbox
        self.__prev = prev_state
        self.__new = new_state

    def undo(self):
        self.__checkbox.setCheckState(self.__prev)

    def redo(self):
        self.__checkbox.setCheckState(self.__new)

class _CheckBoxHelper(object):
    def __init__(self, undo_stack, undo_text):
        srllib.qtgui.connect(self, "stateChanged(int)", self.__state_changed)
        self.__undo_stack = undo_stack
        self.__cur_state = self.checkState()
        self.__undo_txt = undo_text
        # setCheckState will emit stateChanged, so we've got to know when to
        # ignore it
        self.__setting_state = False

    def setCheckState(self, state):
        self.__setting_state = True
        try:
            self._qbase.setCheckState(self, state)
            self.__cur_state = state
        finally: self.__setting_state = False

    def __state_changed(self, state):
        if self.__setting_state:
            return
        undo_stack = self.__undo_stack
        if undo_stack is None:
            return

        # The state parameter is an integer, but a due to an inconsistency in
        # PyQt4 setCheckState will only accept Qt.CheckState objects
        if state == Qt.Checked:
            state = Qt.Checked
        elif state == Qt.Unchecked:
            state = Qt.Unchecked
        undo_stack.push(_CheckBoxUndo(self, self.__cur_state, state,
            self.__undo_txt))
        self.__cur_state = state

class CheckBox(QtGui.QCheckBox, _CheckBoxHelper):
    _qbase = QtGui.QCheckBox

    def __init__(self, label=QtCore.QString(), parent=None, undo_stack=None,
        undo_text=None):
        self.__super.__init__(self, label, parent)
        _CheckBoxHelper.__init__(self, undo_stack, undo_text)
