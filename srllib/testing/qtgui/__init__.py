# Part of Srl Python Components
# Copyright (c) 2007 Srl Research Laboratory

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software
# and associated documentation files (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge, publish, distribute,
# sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
# NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT
# OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
""" Unit testing functionality for Qt-based components. """
from PyQt4.QtGui import *
from PyQt4.QtCore import *

from srllib.testing import *
from srllib.testing.qtgui.mock import QMock
import srllib.qtgui
from srllib import util

class WidgetController(object):
    def __init__(self, app):
        self.__app = app

    def mouseClick(self, widget):
        self.__mouseEvent(widget, QEvent.MouseButtonPress)
        self.__mouseEvent(widget, QEvent.MouseButtonRelease)

    def __mouseEvent(self, w, tp, btn=Qt.LeftButton, pos=None, kbdMods=Qt.NoModifier):
        if pos is None:
            pos = QPoint(w.width() / 2, w.height() / 2)
        e = QMouseEvent(tp, pos, btn, btn, kbdMods)
        self.__app.postEvent(w, e)
        self.__app.processEvents()

class QtTestCase(TestCase):
    """ Baseclass for tests involving Qt, but not necessarily GUI stuff.

    This class replaces QObject.connect and srllib.qtgui.connect in the setup
    phase, with an alternative implementation. The alternative implementation
    detects whether the sender is a QMock instance; if so, it uses
    QMock.connect, otherwise QObject.connect is employed. Using QMock.connect
    means that we gain control of the signal connection/emission process.
    """
    __real_connect = QObject.connect

    def setUp(self):
        TestCase.setUp(self)
        self._set_attr(QObject, "connect", self.__connect)
        self._set_attr(srllib.qtgui, "connect", self.__qtgui_connect)

    def tearDown(self):
        TestCase.tearDown(self)
        QMock.mock_clear_connections()

    def assertConnected(self, slot, emitter, signal):
        """ Assert that a slot is connected to a signal. """
        self.assert_(emitter.mock_is_connected(slot, signal), msg=
            "Slot %r not connected to signal %s of %r" % (slot, signal,
                emitter))

    @classmethod
    def __qtgui_connect(cls, sender, signal, slot):
        """ Simulate srllib.qtgui.connect.

        This function differs from standard QObject.connect by implicitly
        transforming the signal argument with SIGNAL.
        """
        cls.__connect(sender, SIGNAL(signal), slot)

    @classmethod
    def __connect(cls, sender, signal, slot):
        if isinstance(sender, QMock):
            QMock.connect(sender, signal, slot)
        else:
            cls.__real_connect(sender, signal, slot)

class GuiTestCase(QtTestCase):
    QApplicationClass = QApplication
    q_app = None

    def __init__(self, *args, **kwds):
        QtTestCase.__init__(self, *args, **kwds)

    @classmethod
    def create_application(cls):
        import sys
        cls.q_app = cls.QApplicationClass(sys.argv)
        return cls.q_app

    @classmethod
    def close_application(cls):
        if not cls.q_app.has_quit():
            # Perhaps already closed due to an exception?
            cls.q_app.quit()
            cls.q_app.processEvents()
        cls.q_app = None

    def setUp(self, widgetClass=None, *args):
        """ @param widgetClass: Optionally, pass the class of a widget to
        instantiate.
        @param args: Arguments to widget initializer.
        """
        QtTestCase.setUp(self)

        if (self.__class__.q_app is not None):
            # Reuse existing QApplication
            self._app = self.__class__.q_app
            self.__created_app = False
        else:
            # Set up QApplication for this test
            self._app = self.__class__.create_application()
            self.__created_app = True

        assert type(self._app) is self.__class__.QApplicationClass
        self._app.processEvents()
        if widgetClass is not None:
            self._widget = widgetClass(*args)
        self.__qtConns = []
        self._widgetController = WidgetController(self._app)

    def tearDown(self):
        QtTestCase.tearDown(self)

        self._widget.close()
        for sender, sig, slt in self.__qtConns:
            QObject.disconnect(sender, sig, slt)
        if self.__created_app:
            self.close_application()

    def _connectToQt(self, sender, signal, slot):
        QObject.connect(sender, SIGNAL(signal), slot)
        self.__qtConns.append((sender, SIGNAL(signal), slot))

    def _scheduleCall(self, func, interval=0):
        """ Schedule function with Qt event loop to be called after a certain interval.

        @param func: Function to execute.
        @param interval: Interval in seconds.
        """
        QTimer.singleShot(int(interval * 1000), func)
