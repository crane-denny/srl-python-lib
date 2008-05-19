from PyQt4.QtCore import QObject

from srllib.testing.mock import *

class QMock(QObject, Mock):
    """ Mock class that also inherits from QObject.
    """
    __connections = {}

    def __init__(self, *args, **kwds):
        QObject.__init__(self)
        Mock.__init__(self, *args, **kwds)

    @classmethod
    def mock_clear_connections(cls):
        cls.__connections.clear()

    def mock_is_connected(self, slot, signal):
        return slot in self.__connections.setdefault(self, {}
            ).setdefault(signal, [])

    @classmethod
    def connect(cls, emitter, signal, slot):
        cls.__connections.setdefault(emitter, {}).setdefault(signal, []).append(
            slot)

    def emit(self, signal, *args):
        """ Allow signal emission.
        """
        # XXX: Consider slot signature?
        for slot in self.__connections.setdefault(self, {}).setdefault(
            signal, []):
            slot(*args)
        # QObject.emit(self, signal, *args)

class QWidgetMock(QMock):
    def __init__(self):
        QMock.__init__(self)
        self.__enabled = True

    def setEnabled(self, enabled):
        self.__enabled = enabled

    def isEnabled(self):
        return self.__enabled
