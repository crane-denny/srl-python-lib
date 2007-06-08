from PyQt4.QtGui import qApp

def deferredSlot(func, optimize=False):
    def schedule(self, *args, **kwds):
        qApp.queueAsyncEvent(func, args, kwds, optimize)
    return schedule

def deferredSlotOptimize(func):
    return deferredSlot(func, optimize=True)
