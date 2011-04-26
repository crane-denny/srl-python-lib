from srllib.testing import *

try:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtCore import Qt
except ImportError:
    has_qt4 = False

    # Define baseclass in lieu of Qt stuff
    QtTestCase = TestCase
else:
    has_qt4 = True
    from srllib.testing.qtgui import *
    from srllib.testing.qtgui import mock as guimock
    from srllib.testing.qtgui import mocks as guimocks

from srllib.util import (get_os, get_os_name, get_os_version, Os_Linux,
    Os_Windows)


def only_qt4(test):
    """Decorator for tests that are particular to POSIX."""
    if has_qt4:
        return test
    return None
