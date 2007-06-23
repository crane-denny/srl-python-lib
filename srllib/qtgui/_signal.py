from PyQt4.QtGui import qApp

def deferred_slot(func, optimize=False):
    def schedule(self, *args, **kwds):
        qApp.queue_async_event(func, args, kwds, optimize)
    return schedule

def deferred_slot_optimize(func):
    return deferred_slot(func, optimize=True)
