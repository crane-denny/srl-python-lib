import srllib.qtgui
from PyQt4.QtCore import QObject, SIGNAL

def deferred_slot(func, optimize=False):
    def schedule(*args, **kwds):
        srllib.qtgui.get_app().queue_deferred(func, args, kwds, optimize)
    return schedule

def deferred_slot_optimize(func):
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
        @param signal: The Qt signal (as a string).
        @param slot: The slot to be invoked.
        @param extra_args: Extra arguments to pass when invoking the slot.
        """
        QObject.__init__(self, emitter)
        self.__slot, self.__extra = slot, extra_args
        QObject.connect(emitter, SIGNAL(signal), self)

    def __call__(self, *args, **kwds):
        args = args + tuple(self.__extra)
        self.__slot(*args, **kwds)
