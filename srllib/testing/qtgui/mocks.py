""" Mock classes for use with Qt.
"""
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from srllib.testing.qtgui.mock import Mock, QMock, QWidgetMock

class QDockWidgetMock(QWidgetMock):
    _MockRealClass = QDockWidget

class QMenuMock(Mock):
    _MockRealClass = QMenu

    def __init__(self, title=None):
        Mock.__init__(self)
        self.mock_entries = []
        self.__cur_sect = []
        self.mock_entries.append(self.__cur_sect)
        self.mock_title = title

    def mock_get_actions(self):
        """ Get all action entries, indexed on name.

        To find actions, they must be instances of QAction or L{QActionMock}.
        """
        actions = {}
        for sect in self.mock_entries:
            for e in sect:
                if isinstance(e, (QAction, QActionMock)):
                    actions[e.text().replace("&", "").replace(" ", "")] = e
        return actions

    def addAction(self, action):
        self.__cur_sect.append(action)

    def addMenu(self, title):
        menu = QMenuMock()
        self.__cur_sect.append(QMenuMock(title))
        return menu

    def addSeparator(self):
        self.__cur_sect = []
        self.mock_entries.append(self.__cur_sect)

class QActionMock(QMock):
    _MockRealClass = QAction

    def __init__(self, text=None, parent=None):
        QMock.__init__(self, parent)
        self.__enabled = True
        self.__checked = False
        self.__text = text

    def text(self):
        return self.__text

    def setText(self, text):
        self.__text = text

    def setEnabled(self, enabled):
        self.__enabled = enabled

    def isEnabled(self):
        return self.__enabled

    def setChecked(self, checked):
        self.__checked = checked

    def isChecked(self):
        return self.__checked

    def trigger(self):
        self.emit(SIGNAL("triggered()"))

class QActionGroupMock(QMock):
    _MockRealClass = QActionGroup

    def __init__(self, parent=None):
        QMock.__init__(self, parent)
        self.__enabled = True
        self.__actions = []

    def isEnabled(self):
        return self.__enabled

    def setEnabled(self, enabled):
        self.__enabled = enabled

    def addAction(self, action):
        self.__actions.append(action)

class QToolButtonMock(QMock):
    _MockRealClass = QToolButton

    def __init__(self):
        QMock.__init__(self)
        self.__enabled = True

    def setEnabled(self, enabled):
        self.__enabled = enabled

    def click(self):
        self.emit(SIGNAL("clicked()"))

    def isEnabled(self):
        return self.__enabled

class QLabelMock(QWidgetMock):
    _MockRealClass = QLabel

    def __init__(self, text=""):
        QWidgetMock.__init__(self)
        self.__text = text

    def text(self):
        return self.__text

    def setText(self, text):
        self.__text = text

class _ItemMockBase(Mock):
    def __init__(self, model):
        self.model = model

class QPixmapMock(QMock):
    _MockRealClass = QPixmap

class QComboBoxMock(QWidgetMock):
    _MockRealClass = QComboBox

    def __init__(self, *args, **kwds):
        QWidgetMock.__init__(self, *args, **kwds)
        self.mock_items = []

    def addItem(self, item):
        self.mock_items.append(item)

    def addItems(self, items):
        self.mock_items.extend(items)

    def clear(self):
        self.mock_items = []

class QStatusBarMock(QWidgetMock):
    _MockRealClass = QStatusBar

    def __init__(self, *args, **kwds):
        QWidgetMock.__init__(self, *args, **kwds)
        self.mock_permanent_widgets = []

    def addPermanentWidget(self, widget):
        self.mock_permanent_widgets.append(widget)

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

class QToolBoxMock(QWidgetMock):
    _MockRealClass = QToolBox

class QTreeWidgetMock(QWidgetMock):
    _MockRealClass = QTreeWidget

    def __init__(self, *args, **kwds):
        QWidgetMock.__init__(self, *args, **kwds)
        self.mock_items = []

    def addTopLevelItem(self, item):
        self.mock_items.append(item)

    def clear(self):
        self.mock_items = []

class QTreeWidgetItemMock(QWidgetMock):
    _MockRealClass = QTreeWidgetItem


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

class _ButtonMockBase(QWidgetMock):
    def click(self):
        self.emit(SIGNAL("clicked()"))

class QPushButtonMock(_ButtonMockBase):
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

class QCheckBoxMock(QMock):
    _MockRealClass = QCheckBox

    def __init__(self):
        QMock.__init__(self)
        self.__checked = False

    def setChecked(self, checked):
        self.__checked = checked

    def isChecked(self):
        return self.__checked

class QListWidgetMock(QWidgetMock):
    _MockRealClass = QListWidget

    def __init__(self):
        QWidgetMock.__init__(self)
        self.__items = []

    def addItem(self, text):
        self.__items.append(text)

    def count(self):
        return len(self.__items)

class QTableWidgetMock(QWidgetMock):
    _MockRealClass = QTableWidget

    def __init__(self):
        QWidgetMock.__init__(self)
        self.__row_count = self.__col_count = 0
        self.mock_items = []
        self.mock_cell_widgets = []

    def rowCount(self):
        return self.__row_count

    def setRowCount(self, count):
        self.__row_count = count

    def setColumnCount(self, count):
        self.__col_count = count

    def columnCount(self):
        return self.__col_count

    def item(self, row, col):
        return self.mock_items[row].get(col)

    def setItem(self, row, col, item):
        items = self.mock_items
        while row >= len(items):
            items.append({})
        items[row][col] = item

    def takeItem(self, row, col):
        return self.mock_items[row].pop(col)

    def cellWidget(self, row, col):
        return self.mock_cell_widgets[row].get(col)

    def setCellWidget(self, row, col, widget):
        items = self.mock_cell_widgets
        while row >= len(items):
            items.append({})
        items[row][col] = widget

class QTableWidgetItemMock(QMock):
    _MockRealClass = QTableWidgetItem

class QIconMock(QMock):
    _MockRealClass = QIcon

class QFileMock(QMock):
    _MockRealClass = QFile

class QTextStreamMock(QMock):
    _MockRealClass = QTextStream
