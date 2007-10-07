from PyQt4.QtCore import QObject

from srllib.testing.mock import *

class QMock(QObject, Mock):
    """ Mock class that also inherits from QObject.
    """
    __connections = {}
    
    def __init__(self):
        QObject.__init__(self)
        Mock.__init__(self)
        
    @classmethod
    def connect(cls, sender, signal, slot):
        cls.__connections.setdefault((sender, signal), set()).add(slot)
        
    @classmethod
    def mock_clear_connections(cls):
        cls.__connections.clear()
        
    def emit(self, signal, *args):
        slots = self.__connections.get((self, signal), [])
        if not slots:
            print "No connections for %s" % signal
        for slot in slots:
            slot(*args)
            