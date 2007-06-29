""" Functionality on top of QApplication.
"""
import sys, traceback, signal, Queue
from PyQt4.QtGui import *
from PyQt4.QtCore import QEvent, QTimer, QObject, SIGNAL

from srllib.signal import Signal
from _common import *

__all__ = ["Application"]

class _AsyncEvent(QEvent):
    EventType = QEvent.User

    def __init__(self, func, obj, args, kwds):
        QEvent.__init__(self, self.__class__.EventType)
        self.func, self.obj, self.args, self.kwds = func, obj, args, kwds
        import threading
        self.dispatch_event = threading.Event()

class Application(QApplication):
    """ Specialize QApplication to trap Python exceptions, inform the user and quit.
    @cvar the_app: The L{application<Application>} object, if instantiated (otherwise None).
    @ivar sig_exception: Emitted when detecting an unhandled exception.
    """
    import srllib.signal
    sig_quitting = srllib.signal.Signal()
    the_app = None

    def __init__(self, argv=sys.argv, catchExceptions=True):
        import PyQt4.QtGui
        print "Jhuhu!"
        QApplication.__init__(self, argv)

        self.sig_exception = Signal()

        self.__once, self.__hasQuit, self.__callQueue = True, False, []
        if catchExceptions:
            sys.excepthook = self.__exchook
        PyQt4.QtGui.qApp = self
        Application.the_app = self

        self.__deferredQueue = Queue.Queue()
        timer = self.__timer = QTimer(self)
        QObject.connect(timer, SIGNAL("timeout()"), self.__slot_timed_out)
        timer.start(20)

    # Qt methods

    @staticmethod
    def setOverrideCursor(cursor):
        """ Set overriding cursor for application. Argument cursor should either be suitable
        enumeration or a QCursor. """
        if type(cursor) is not QCursor:
            QApplication.setOverrideCursor(QCursor(cursor))
        else:
            QApplication.setOverrideCursor(cursor)

    def customEvent(self, e):
        if not isinstance(e, _AsyncEvent):
            return QApplication.customEvent(self, e)
        e.func(e.obj, *e.args, **e.kwds)
        e.dispatch_event.set()

    @classmethod
    def quit(cls):
        assert not cls.the_app.__hasQuit, "The app has already quit"
        cls.sig_quitting()
        QApplication.quit()
        cls.the_app.__hasQuit = True

    #}

    def queue_call(self, toCall, args=None, kwds=None):
        """ Queue a call for when control returns to the event loop. """
        args = args or ()
        kwds = kwds or {}
        self.__callQueue.append((toCall, args, kwds))
        QTimer.singleShot(0, self.__exec_call)

    def queue_deferred(self, mthd, args, kwds):
        """ Queue deferred method call to be dispatched in GUI thread. """
        self.__deferredQueue.put((mthd, args, kwds))

    def __slot_timed_out(self):
        """ Periodic callback for various chores.
        
        This callback is here used to dispatch background-thread events, and as an opportunity for
        Python to process incoming OS signals (e.g., SIGINT resulting from Ctrl+C).
        """
        # Find deferred calls and dispatch them

        toDispatch = []
        while True:
            try: mthd, args, kwds, optimize = self.__deferredQueue.get_nowait()
            except Queue.Empty:
                break
            toDispatch.append((mthd, args, kwds, optimize))

        last = None
        i = len(toDispatch) - 1
        for mthd, args, kwds, optimize in reversed(toDispatch):
            if mthd is last and optimize:
                # Don't call several times
                del toDispatch[i]
            last = mthd
            i -= 1
        for mthd, args, kwds, optimize in toDispatch:
            mthd(*args, **kwds)

    def __exchook(self, exc, value, tb):
        if self.__once:
            self.__once = False

            self.sig_exception(exc, value, tb)

            self.__timer.stop()
            import srllib.threading
            thrdSpecific = ""
            if exc is srllib.threading.ThreadError:
                thrdSpecific = " in thread %s" % (value.thread,)
                exc, value, tb = value.excType, value.exc, value.tb
                
            msg = ' '.join(traceback.format_exception(exc, value, tb))

            messageCritical("Fatal Error", "An unexpected exception was encountered%s, \
the application will have to be shut down." % (thrdSpecific,), detailedText=msg, informativeText=\
"The detailed text provides full technical information of how the error happened, so \
developers may resolve the problem. This information should also be visible in the application log.")

            if not self.__hasQuit:
                self.quit()
            self.processEvents()

    def __exec_call(self):
        toCall, args, kwds = self.__callQueue.pop(0)
        toCall(*args, **kwds)
        
def get_app():
    """ Get the current L{Application} instance. """
    return Application.the_app

