""" Test QApplication wrapper. """
from srllib.qtgui import Application
from PyQt4.QtCore import QTimer

from _common import *

class ApplicationTest(TestCase):
    def test_set_excepthook(self):
        def exchook(exc, value, tb, threadname):
            self.__invoked = (exc, value, tb, threadname)
            
        def raiser():
            print "Raising"
            raise KeyboardInterrupt
        
        def quitter():
            Application.instance().quit()
            
        app = Application()
        app.sig_exception.connect(exchook)
        QTimer.singleShot(0, raiser)
        QTimer.singleShot(1, quitter)
        self.__invoked = None
        app.exec_()
        try: exc = self.__invoked[0]
        except TypeError:
            self.fail("Exception hook not called")
        self.assertIs(exc, KeyboardInterrupt, "Unexpected exception type: %r" % exc)