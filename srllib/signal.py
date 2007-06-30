""" Signals/slots functionality. """
import types, weakref

from error import *

class _DeadReference(SrlError):
    pass

class _FunctionProxy(object):
    def __init__(self, func):
        self._ref = weakref.ref(func)

    def __call__(self, *args, **kwds):
        func = self._getRef()
        func(*args, **kwds)

    def __eq__(self, rhs):
        func = self._getRef()
        return func == rhs

    @property
    def object(self):
        return self._ref()

    def _getRef(self):
        func = self._ref()
        if func is None:
            raise _DeadReference
        return func

class CallFailure(SrlError):
    """ Failure to call slot. """

class _MethodProxy(object):
    def __init__(self, mthd):
        self._instanceRef, self._mthdRef = weakref.ref(mthd.im_self), weakref.ref(mthd.im_func)

    def __call__(self, *args, **kwds):
        instance, mthd = self._get_refs()
        try: mthd(instance, *args, **kwds)
        except TypeError, err:
            raise CallFailure("Calling slot %s.%s resulted in TypeError, check \
your arguments; the original exception was: `%s'" %
                    (mthd.__module__, mthd.__name__, err.message,))

    def __eq__(self, rhs):
        if isinstance(rhs, _MethodProxy):
            return self._get_refs() == rhs._get_refs()

        if type(rhs) != types.MethodType:
            return False
        instance, mthd = self._get_refs()
        return instance == rhs.im_self and mthd == rhs.im_func

    @property
    def object(self):
        return self._instanceRef()

    def _get_refs(self):
        instance, mthd = self._instanceRef(), self._mthdRef()
        if instance is None:
            raise _DeadReference
        assert mthd is not None
        return instance, mthd

class Signal(object):
    """ A signal is a way to pass a message to interested observers.
    
    Observers connect methods ("slots") to the signal they're interested in, and when the
    signal is fired the methods are called back with the correct parameters.
    """
    __all_signals = set()

    def __init__(self):
        self._slots = []
        self.__obj2slots = {}
        Signal.__all_signals.add(self)
        self.__enabled = True
	
    def __call__(self, *args, **kwds):
        """ For each group in sorted order, call each slot.
        """ 
        if not self.__enabled:
            return

        for e in self._slots[:]:
            slot, defArgs, defKwds = e
            args += tuple(defArgs[len(args):])
            keywords = defKwds.copy()
            keywords.update(kwds)
            try:
                slot(*args, **keywords)
            except _DeadReference:
                self._slots.remove(e)

    def connect(self, slot, defArgs=(), defKwds={}):
        """ Connect this signal to a slot, alternatively grouped. Optionally,
        keywords can be bound to slot.
        """
        if isinstance(slot, types.MethodType):
            prxyTp = _MethodProxy
        else:
            prxyTp = _FunctionProxy
        self.__connect(prxyTp(slot), defArgs, defKwds)

    def disconnect(self, slot):
        """ Disconnect signal from slot.
        @raise ValueError: Not connected to slot.
        """
        e = self.__find_slot(slot)
        if e is None:
            raise ValueError(slot)
        self.__remove_entry(e)

    @classmethod
    def disconnect_all_signals(cls, obj):
        """ Disconnect all signals from an object and its methods.
        
        @note: If no connections are found for this object, no exception is raised.
        """
        for sig in cls.__all_signals:
            if sig.is_connected(obj):
                sig.disconnect_object(obj)

    def disconnect_object(self, obj):
        """ Disconnect an object and its methods. """
        objSlots = self.__obj2slots[obj]
        for s in objSlots:
            self.disconnect(s)

    def enable(self):
        self.__enabled = True

    def disable(self):
        self.__enabled = False

    def set_enabled(self, enabled):
        self.__enabled = enabled

    def is_connected(self, obj):
        """ Is an object connected to this signal. """
        return obj in self.__obj2slots

    def __connect(self, slot, defArgs, defKwds):
        e = (slot, defArgs, defKwds)
        if self.__find_slot(slot) is None:
            self._slots.append(e)

        if not slot.object in self.__obj2slots:
            self.__obj2slots[slot.object] = []
        self.__obj2slots[slot.object].append(slot)

    def __find_slot(self, slot):
        for e in self._slots[:]:
            try:
                if e[0] == slot:
                    return e
            except _DeadReference:
                self.__remove_entry(e)

    def __remove_entry(self, entry):
        self._slots.remove(entry)
        slot = entry[0]
        objSlots = self.__obj2slots[slot.object]
        objSlots.remove(slot)
        if not objSlots:
            del self.__obj2slots[slot.object]

