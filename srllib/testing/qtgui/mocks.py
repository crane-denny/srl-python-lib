""" Mock classes for use with Qt.
"""
from PyQt4.QtGui import (QButtonGroup, QGroupBox, QPushButton, QRadioButton,
        QLineEdit, QCheckBox, QToolButton, QFileDialog, QListWidget)
from PyQt4.QtCore import SIGNAL

from srllib.testing.qtgui.mock import Mock, QMock, QWidgetMock

class QButtonGroupMock(QMock):
    _MockRealClass = QButtonGroup

    def __init__(self):
        QMock.__init__(self)
        self.__btns = {}
        self.__checked = None

    def mock_set_checked(self, btn):
        self.__checked = btn
        for b in self.__btns.values():
            if b.isChecked() and b is not btn:
                b.setChecked(False)

    def addButton(self, btn, id):
        self.__btns[id] = btn
        btn.mock_group = self

    def button(self, id):
        return self.__btns[id]

    def checkedButton(self):
        return self.__checked

    def checkedId(self):
        for i, b in self.__btns.items():
            if b is self.__checked:
                return i

class QGroupBoxMock(QMock):
    _MockRealClass = QGroupBox

    def __init__(self):
        QMock.__init__(self)
        self.__checked = True
        self.__checkable = False

    def isCheckable(self):
        return self.__checkable

    def setCheckable(self, checkable):
        self.__checkable = checkable

    def isChecked(self):
        return self.__checkable and self.__checked

class QPushButtonMock(QWidgetMock):
    _MockRealClass = QPushButton

class QRadioButtonMock(QMock):
    _MockRealClass = QRadioButton

    def __init__(self):
        QMock.__init__(self)
        self.__checked = False
        self.mock_group = None

    def setChecked(self, checked):
        self.__checked = checked
        if self.mock_group is not None:
            self.mock_group.mock_set_checked(self)

    def isChecked(self):
        return self.__checked

class QLineEditMock(QMock):
    _MockRealClass = QLineEdit

    def __init__(self):
        QMock.__init__(self)
        self.__text = ""

    def setText(self, text):
        self.__text = text
        self.emit(SIGNAL("textEdited(const QString&)"), text)

    def text(self):
        return self.__text

class QCheckBoxMock(QMock):
    _MockRealClass = QCheckBox

    def __init__(self):
        QMock.__init__(self)
        self.__checked = False

    def setChecked(self, checked):
        self.__checked = checked

    def isChecked(self):
        return self.__checked

class QToolButtonMock(QMock):
    _MockRealClass = QToolButton

    def click(self):
        self.emit(SIGNAL("clicked()"))

class QListWidgetMock(QWidgetMock):
    _MockRealClass = QListWidget

    def __init__(self):
        QWidgetMock.__init__(self)
        self.__items = []

    def addItem(self, text):
        self.__items.append(text)

    def count(self):
        return len(self.__items)
