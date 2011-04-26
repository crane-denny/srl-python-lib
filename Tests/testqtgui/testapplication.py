""" Test QApplication wrapper. """
from _common import *

if has_qt4:
    from srllib.qtgui import Application
    from PyQt4.QtCore import QTimer

@only_qt4
class ApplicationTest(TestCase):
    def test_set_excepthook(self):
        def exchook(exc, value, tb, threadname):
            self.__invoked = (exc, value, tb, threadname)
            
        def raiser():
            raise KeyboardInterrupt
        
        def quitter():
            Application.instance().quit()
            
        app = Application()
        app.sig_exception.connect(exchook)
        QTimer.singleShot(0, raiser)
        QTimer.singleShot(1, quitter)
        self.__invoked = None
        app.exec_()
        try: exc, val, tb = self.__invoked[:3]
        except TypeError:
            self.fail("Exception hook not called")
        if exc is not KeyboardInterrupt:
            import traceback; traceback.print_exception(exc, val, tb)
            self.fail("Unexpected exception type: %r" % exc)
