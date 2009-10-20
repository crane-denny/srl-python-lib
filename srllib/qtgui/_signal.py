import srllib.qtgui
from PyQt4.QtCore import QObject, SIGNAL
import functools

def deferred_slot(func, optimize=False):
    """ Decorator for turning a method into a deferred slot.

    When calling a deferred slot, it is queued with the QApplication (must be
    a L{srllib.qtgui.Application} instance). Queued calls are dispatched
    periodically, which saves CPU time as opposed to making GUI calls directly
    as signals are received.
    """
    @functools.wraps(func)
    def schedule(*args, **kwds):
        srllib.qtgui.get_app().queue_deferred(func, args, kwds, optimize)
    return schedule

def deferred_slot_optimize(func):
    """ Optimized version of L{deferred_slot}.

    Optimization happens by only queueing one call to a slot at a time.
    """
    return deferred_slot(func, optimize=True)

class StatefulConnection(QObject):
    """ A connection between a Qt signal and a slot, which is capable of
    storing an extra set of arguments to the slot.

    We subclass QObject and make instances children of the signal emitter,
    so that their lifetime is bound to the latter.
    """
    def __init__(self, emitter, signal, slot, extra_args=[]):
        """
        @param emitter: The signal emitter.
        @param signal: Signal signature (PyQt4.QtCore.Signal is invoked on this).
        @param slot: The slot to be invoked.
        @param extra_args: Extra arguments to pass when invoking the slot.
        """
        QObject.__init__(self, emitter)
        self.__slot, self.__extra = slot, extra_args
        QObject.connect(emitter, SIGNAL(signal), self)

    def __call__(self, *args, **kwds):
        args = args + tuple(self.__extra)
        self.__slot(*args, **kwds)

def connect(emitter, signal, slot):
    """ Simplified version of QObject.connect which takes a raw slot signature.

    @param emitter: Signal emitter.
    @param signal: Signal signature (PyQt4.QtCore.Signal is invoked on this).
    @param slot: Signal signature (PyQt4.QtCore.Signal is invoked on this).
    """
    QObject.connect(emitter, SIGNAL(signal), slot)
