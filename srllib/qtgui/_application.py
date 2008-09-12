""" Functionality on top of QApplication.
"""
import sys, traceback, Queue
from PyQt4.QtGui import *
import warnings

import srllib.threading
from srllib.signal import Signal
from _common import *
from srllib.qtgui import _signal

__all__ = ["Application", "get_app"]

class _AsyncEvent(QEvent):
    EventType = QEvent.User

    def __init__(self, func, obj, args, kwds):
        QEvent.__init__(self, self.__class__.EventType)
        self.func, self.obj, self.args, self.kwds = func, obj, args, kwds
        self.dispatch_event = srllib.threading.Event()

class Application(QApplication):
    """ Specialize QApplication to trap Python exceptions, inform the user and quit.
    @cvar the_app: The L{application<Application>} object, if instantiated
    (otherwise None).
    @ivar sig_exception: Emitted when detecting an unhandled exception.
    Parameters: Exception type, exception value, traceback, name of thread (None
    if main thread).
    """
    import srllib.signal
    sig_quitting = srllib.signal.Signal()
    the_app = None

    def __init__(self, argv=None, catch_exceptions=True):
        """
        @param catch_exceptions: Handle uncaught exceptions.
        """
        if argv is None:
            # sys.argv needn't be defined when embedding Python
            argv = getattr(sys, "argv", [])
        QApplication.__init__(self, argv)

        self.sig_exception = Signal()

        self.__hasQuit, self.__call_queue = False, []
        if catch_exceptions:
            sys.excepthook = self.__exchook
            srllib.threading.register_exceptionhandler(self.__thrdexc_hook)

        import PyQt4.QtGui
        PyQt4.QtGui.qApp = self
        Application.the_app = self

        self.__deferred_queue = Queue.Queue()
        timer = self.__timer = QTimer(self)
        QObject.connect(timer, SIGNAL("timeout()"), self.__slot_timed_out)
        timer.start(20)

    #{ Qt methods

    @staticmethod
    def setOverrideCursor(cursor):
        """ Set overriding cursor for application. Argument cursor should either
        be suitable enumeration or a QCursor.
        """
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
        if cls.the_app.__hasQuit:
            warnings.warn("The app has already quit")
        cls.sig_quitting()
        QApplication.quit()
        cls.the_app.__hasQuit = True

    @classmethod
    def has_quit(cls):
        return cls.the_app.__hasQuit

    #}

    def queue_call(self, to_call, args=None, kwds=None):
        """ Queue a call for when control returns to the event loop.
        """
        args = args or ()
        kwds = kwds or {}
        self.__call_queue.append((to_call, args, kwds))
        QTimer.singleShot(0, self.__exec_call)

    def queue_deferred(self, mthd, args, kwds, optimize=False):
        """ Queue deferred method call to be dispatched in GUI thread.
        """
        self.__deferred_queue.put((mthd, args, kwds, optimize))

    def __slot_timed_out(self):
        """ Periodic callback for various chores.

        This callback is here used to dispatch background-thread signals, and
        as an opportunity for Python to process incoming OS signals (e.g.,
        SIGINT resulting from Ctrl+C).
        """
        # Find deferred calls and dispatch them

        to_dispatch = []
        while True:
            try: mthd, args, kwds, optimize = self.__deferred_queue.get_nowait()
            except Queue.Empty:
                break
            to_dispatch.append((mthd, args, kwds, optimize))

        last = None
        i = len(to_dispatch) - 1
        for mthd, args, kwds, optimize in reversed(to_dispatch):
            if mthd is last and optimize:
                # Don't call several times
                del to_dispatch[i]
            last = mthd
            i -= 1
        for mthd, args, kwds, optimize in to_dispatch:
            mthd(*args, **kwds)

    @_signal.deferred_slot
    def __thrdexc_hook(self, exc):
        self.__exchook(exc.exc_type, exc.exc_value, exc.exc_traceback,
                in_thread=exc.name)

    def __exchook(self, exc, value, tb, in_thread=None):
        self.sig_exception(exc, value, tb, in_thread)

        self.__timer.stop()
        # Don't act on Ctrl+C
        if not exc is KeyboardInterrupt:
            thrdSpecific = ""
            if in_thread:
                thrdSpecific = " in thread %s" % (in_thread,)

            msg = ' '.join(traceback.format_exception(exc, value, tb))
            message_critical("Fatal Error", "An unexpected exception was "
                    "encountered%s, the application will have to be shut "
                    "down." % (thrdSpecific,), detailed_text=msg,
                    informative_text="The detailed text provides full technical "
                    "information of how the error happened, so developers may "
                    "resolve the problem. This information should also be "
                    "visible in the application log.")

        if not self.__hasQuit:
            self.quit()
        self.processEvents()

    def __exec_call(self):
        toCall, args, kwds = self.__call_queue.pop(0)
        toCall(*args, **kwds)

_the_app = None

def get_app():
    """ Get the current L{Application} instance. """
    global _the_app
    if _the_app is not None:
        # Allow overriding of application, useful for tests
        return _the_app
    return Application.the_app
