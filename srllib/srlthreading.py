""" Threading logic.

The functionality here improves upon that in the standard L{threading} module.
"""
import threading, os.path, traceback

from srllib import util
from srllib.error import *

class ThreadError(SrlError):
    def __init__(self, name, exc_info):
        SrlError.__init__(self, "An exception was caught in thread '%s':\n%s" %
                          (name, " ".join(traceback.format_exception(*exc_info))))

class Cancellation(Exception):
    pass

class TimeoutError(Exception):
    pass

def _def_handler(thread_exc):
    print thread_exc
_prev_handler = _exc_handler = _def_handler

def register_exceptionhandler(handler):
    """ Register a handler for exceptions happening in background thread.

    The exception handler will receive a L{ThreadError}. """
    global _exc_handler, _prev_handler
    if _prev_handler != handler:
        _prev_handler = handler
    _exc_handler = handler

def restore_exceptionhandler():
    """ Restore global exception handler to previous one. """
    global _exc_handler, _prev_handler
    _exc_handler = _prevExcHandler

def synchronized(func):
    """ Decorator for making functions thread-safe. """
    def syncfunc(*args, **kwds):
        func._sync_lock.acquire()
        try: r = func(*args, **kwds)
        finally: func._sync_lock.release()
        return r
    
    func._sync_lock = threading.Lock()
    return syncfunc

_thread_specific = {}

class Lock(object):
    def __init__(self, *args, **kwds):
        self._lk = threading.Lock()
        self.__inError = None

    def acquire(self, *args, **kwds):
        ret = self._lk.acquire(*args, **kwds)
        if ret:
            global _thread_specific
            try:
                locks = _thread_specific[Thread.currentThread()]["locks"]
                locks.append(self)
            except KeyError:
                pass
        if self.__inError:
            raise self.__inError
        return ret

    def release(self, *args, **kwds):
        if self._lk.locked():
            self._lk.release(*args, **kwds)
        global _thread_specific
        try:
            locks = _thread_specific[Thread.currentThread()]["locks"]
            if self in locks:
                locks.remove(self)
        except KeyError:
            pass

    def forceRelease(self, exception=None):
        """ Called by Thread upon in order to forcefully release locks upon exit.
        
        Since held locks are released in an abnormal manner, this will cause the waiting thread to
        receive an exception from acquire().
        """
        self.__inError = exception
        self.release()

class Condition(threading._Condition):
    """ Reimplement threading.Condition in order to provide own Lock implementation as default. This is
    because our own Lock supports forceful release. """
    __super = threading._Condition

    def __init__(self, lock=None):
        if lock is None:
            lock = Lock()
        Condition.__super.__init__(self, lock)
        self.__exc = None

    def wait(self, *args, **kwds):
        Condition.__super.wait(self, *args, **kwds)
        if self.__exc is not None:
            raise self.__exc

    def notifyException(self, exception):
        self.__exc = exception
        self.acquire()
        self.notify()
        self.release()

class Event(object):
    def __init__(self):
        self.__cond = Condition()
        self.__flag = False

    def isSet(self):
        return self.__flag

    def set(self):
        self.__cond.acquire()
        try:
            self.__flag = True
            self.__cond.notifyAll()
        finally:
            self.__cond.release()

    def clear(self):
        self.__cond.acquire()
        try:
            self.__flag = False
        finally:
            self.__cond.release()

    def wait(self, timeout=None):
        self.__cond.acquire()
        try:
            if not self.__flag:
                self.__cond.wait(timeout)
        finally:
            self.__cond.release()

class SynchronousCondition(object):
    """ Synchronize two threads, by having one signal a condition and wait until the other receives
    it. """
    def __init__(self):
        self.__notified, self.__waited = Event(), Event()
        self.__exc = None

    def wait(self):
        """ Wait for condition to become true. """
        if Thread._threadLocal.eventCancel.isSet():
            return
        self.__notified.wait()
        self.__notified.clear()
        self.__waited.set()
        if self.__exc is not None:
            raise self.__exc

    def notify(self):
        """ Signal that condition holds true, wait until other thread gets the message. """
        self.__notified.set()
        if Thread._threadLocal.eventCancel.isSet():
            return
        self.__waited.wait()
        self.__waited.clear()

    def notifyException(self, exception):
        """ Notify waiting threads of exception. """
        self.__exc = exception
        self.__notified.set()
        self.__waited.set()

def testCancel():
    thrd = Thread.currentThread()
    thrd.testCancel()

class Thread(object):
    _thread_local = threading.local()
    _thread_local.current = None

    class _DummyThread:
        """ Dummy class for objects that get returned by current_thread if no Thread is controlling the current thread. """
        def __init__(self):
            self.name = "Dummy"
        
        def test_cancel(self):
            pass
    
    def __init__(self, target=None, args=[], kwds={}, name=None, daemon=False, start=False,
                slot_finished=util.no_op):
        """ @param target: function to execute in background thread
        @param args: arguments to target
        @param kwds: keywords to target
        @param name: thread's name
        @param daemon: die with the main thread?
        @param start: start at once?
        @param slot_finished: a function to invoke once the thread finishes
        """
        self._thrd = threading.Thread(target=self._run, name=name)
        self._trgt, self._args, self._kwds = target, args, kwds
        self._slot_finished = slot_finished
        self.__eventCancel = Event()
        global _exc_handler
        self.__exc_handler = _exc_handler

        """
        for mthd in ("join",):
            setattr(self, mthd, getattr(self._thrd, mthd))
            """
            
        if daemon:
            self.daemon = True

        if start:
            self.start()

    def __str__(self):
        return self.name

    @classmethod
    def current_thread(cls):
        cur = cls._thread_local.current
        if cur is None:
            return Thread._DummyThread()
        return cur

    def __getName(self):
        return self._thrd.getName()
    def __setName(self, name):
        self._thrd.setName(name)
    name = property(__getName, __setName)

    def __isDaemon(self):
        return self._thrd.isDaemon()
    def __setDaemon(self, daemon):
        self._thrd.setDaemon(daemon)
    daemon = property(__isDaemon, __setDaemon)

    @property
    def alive(self):
        return self._thrd.isAlive()

    def start(self):
        self._thrd.start()

    def join(self):
        self._thrd.join()

    @synchronized
    def cancel(self, wait=False, timeout=None):
        """ Tell this thread to cancel itself. Will wait till the request is honoured.
        It is also possible that the thread finishes its execution independently of this request,
        this function will return anyway when it notices that the thread is no longer running. """
        assert Thread.current_thread() is not self
        self.__eventCancel.set()
        if wait:
            self.join(timeout=timeout)
            if self.alive:
                raise TimeoutError

        self._release_locks()

    def test_cancel(self):
        assert Thread.current_thread() is self
        if self.__eventCancel.isSet():
            
            # Clear event, so that it can be reused
            self.__eventCancel.clear()
            raise Cancellation

    def run(self):
        if self._trgt is None:
            raise NotImplementedError
        self._trgt(*self._args, **self._kwds)

    def register_exception_handler(self, handler):
        """ Set exception handler for this thread. """
        self.__exc_handler = handler

    def unregister_exception_handler(self):
        """ Unset exception handler for this thread. """
        global _exc_handler
        self.__exc_handler = _exc_handler

    def _run(self):
        Thread._thread_local.current = self
        global _thread_specific
        _thread_specific[self] = {"locks": []}
        thrd_exc = None

        try:
            self.run()
        except Cancellation:
            pass
        except:
            import sys
            thrd_exc = ThreadError(self.name, sys.exc_info())
            self.__exc_handler(thrd_exc)
        else:
            self._slot_finished()
        finally:
            # Release all locks held by this thread
            self._release_locks(thrd_exc)
        
    def _release_locks(self, exception=None):
        global _thread_specific
        if not self in _thread_specific:
            return
        for lk in _thread_specific[self]["locks"]:
            lk.forceRelease(exception)
        _thread_specific[self]["locks"] = []