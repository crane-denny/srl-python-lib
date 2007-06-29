from srllib.qtgui._application import get_app

def deferred_slot(func, optimize=False):
    def schedule(*args, **kwds):
        get_app().queue_deferred(func, args, kwds, optimize)
    return schedule

def deferred_slot_optimize(func):
    return deferred_slot(func, optimize=True)
