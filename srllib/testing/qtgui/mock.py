from PyQt4.QtCore import QObject

from srllib.testing.mock import *

class QMock(QObject, Mock):
    """ Mock class that also inherits from QObject.
    """
    def __init__(self):
        QObject.__init__(self)
        Mock.__init__(self)