from PyQt4.QtCore import QObject

from srllib.testing.mock import *

class QMock(QObject, Mock):
    """ Mock class that also inherits from QObject.
    """
    __connections = {}

    def __init__(self, *args, **kwds):
        QObject.__init__(self)
        Mock.__init__(self, *args, **kwds)

    def emit(self, signal, *args):
        """ Allow signal emission.
        """
        QObject.emit(self, signal, *args)

class QWidgetMock(QMock):
    def __init__(self):
        QMock.__init__(self)
        self.__enabled = True

    def setEnabled(self, enabled):
        self.__enabled = enabled

    def isEnabled(self):
        return self.__enabled
