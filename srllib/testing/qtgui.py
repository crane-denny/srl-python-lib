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

class GuiTestCase(TestCase):
    __qAppInitialized = False
    QApplicationClass = QApplication

    def __init__(self, *args, **kwds):
        TestCase.__init__(self, *args, **kwds)

    @classmethod
    def createApplication(cls):
        import sys
        qApp = cls.qApp = cls.QApplicationClass(sys.argv)
        return qApp

    def setUp(self, widgetClass, *args):
        """ @param widgetClass: Widget class to instantiate.
        @param args: Arguments to widget initializer.
        """
        TestCase.setUp(self)
        self._app = self.__class__.createApplication()
        assert type(self._app) is self.__class__.QApplicationClass
        self._app.processEvents()
        self._widget = widgetClass(*args)
        self.__qtConns = []
        self._widgetController = WidgetController(self._app)

    def tearDown(self):
        TestCase.tearDown(self)

        self._widget.close()
        for sender, sig, slt in self.__qtConns:
            QObject.disconnect(sender, sig, slt)
        if not self._app.has_quit():
            self._app.quit()
        self._app.processEvents()

    def _connectToQt(self, sender, signal, slot):
        QObject.connect(sender, SIGNAL(signal), slot)
        self.__qtConns.append((sender, SIGNAL(signal), slot))

    def _scheduleCall(self, func, interval=0):
        """ Schedule function with Qt event loop to be called after a certain interval.
        
        @param func: Function to execute.
        @param interval: Interval in seconds.
        """
        QTimer.singleShot(int(interval * 1000), func)
