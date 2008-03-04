from PyQt4.QtCore import *
from PyQt4.QtGui import *

from igmtesting.mock import Mock

import IGMGUI._visualize as guivisualize
import IGMGUI._workflow as guiworkflow

class QMock(QObject, Mock):
    def __init__(self, parent=None, *args, **kwds):
        QObject.__init__(self)
        Mock.__init__(self, *args, **kwds)
        self.__parent = parent

    def parent(self):
        return self.__parent

class QWidgetMock(QMock):
    """ Baseclass for mocks of QWidget descendants.
    @ivar mock_is_hidden: Has this widget been told to hide itself?
    """
    _MockRealClass = QWidget

    def __init__(self, *args, **kwds):
        QMock.__init__(self, *args, **kwds)
        self.mock_is_hidden = False

    def show(self):
        self.setHidden(False)

    def hide(self):
        self.setHidden(True)

    def setHidden(self, hidden):
        self.mock_is_hidden = hidden

    def rect(self):
        return QRect()

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

class GraphicsSceneMock(Mock):
    _MockRealClass = guivisualize._GraphicsScene

    def __init__(self):
        Mock.__init__(self)
        self.__class__.mock_instance = self
        self.model2gui = {}
        self.viewmode = guivisualize.ViewMode_Workflow
        self.is_editable = True

class GraphicsViewMock(QMock):
    _MockRealClass = guivisualize.GraphicsView

class _ItemMockBase(Mock):
    def __init__(self, model):
        self.model = model

class PortItemMock(_ItemMockBase):
    _MockRealClass = guiworkflow._Port

    def __init__(self, model, parent, scene):
        _ItemMockBase.__init__(self, model)

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

class QLineEditMock(QWidgetMock):
    _MockRealClass = QLineEdit

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
