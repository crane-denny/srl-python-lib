from zope.interface import Interface

from srllib.testing.mock import Mock
import srllib.inspect

class InterfaceMock(Mock):
    """ Mock with special support for zope.interface.
    """
    def __init__(self, *args, **kwds):
        dontMock = kwds["dontMock"] = []
        for name in srllib.inspect.get_members(Interface, callable,
            include_bases=False):
            dontMock.append(name)
        Mock.__init__(self, *args, **kwds)