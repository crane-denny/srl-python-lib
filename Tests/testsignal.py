""" Test the signal module. """
from srllib.signal import *

from _common import *

class _Slot:
    def __call__(self):
        pass

class SignalTest(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.__emitted = False

    def testSignal(self):
        sig = self.__getSignal()
        sig("arg1", "arg2", kwd1=None)
        self.assertEqual(self.__emitted, (("arg1", "arg2"), {"kwd1": None}))

        def slot():
            self.__emitted = True

        # Just verify that function slots work
        self.__emitted = False
        sig = self.__getSignal(slot=slot)
        sig()
        self.assert_(self.__emitted)

    def testEnabling(self):
        """ Test enabling/disabling signal. """
        sig = self.__getSignal()
        self.assert_(sig.is_enabled)
        sig.disable()
        self.assertNot(sig.is_enabled)
        sig()
        self.assertNot(self.__emitted)
        sig.enable()
        self.assert_(sig.is_enabled)
        sig()
        self.assert_(self.__emitted)

    def testDisconnect(self):
        sig = self.__getSignal()
        sig.disconnect(self.__slot)
        sig()
        self.assertNot(self.__emitted)
        self.assertRaises(ValueError, sig.disconnect, self.__slot)

    def testDisconnectAllSignals(self):
        """ Test disconnecting from all signals. """
        sig0, sig1 = self.__getSignal(), self.__getSignal()
        Signal.disconnect_all_signals(self)
        sig0()
        sig1()
        self.assertNot(self.__emitted)
        # This shouldn't be an error
        Signal.disconnect_all_signals(self)
        
    def test_is_connected_yes(self):
        def slot():
            pass
        sig = self.__getSignal(slot)
        self.assert_(sig.is_connected(slot))
        
    def test_is_connected_no(self):
        def slot():
            pass
        sig = self.__getSignal()
        self.assertNot(sig.is_connected(slot))

    ''' Can't seem to make this work (force gc)
    def testDeadSlot(self):
        class Slot:
            def __call__(self, *args):
                pass
        slot = Slot()
        sig = self.__getSignal(slot=slot)
        import gc
        del slot
        gc.collect()
        sig()
    '''

    def __slot(self, *args, **kwds):
        self.__emitted = (args, kwds)

    def __getSignal(self, slot=None):
        if slot is None:
            slot = self.__slot
        sig = Signal()
        sig.connect(slot)
        return sig
