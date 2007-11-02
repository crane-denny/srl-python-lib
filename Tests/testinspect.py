import inspect

import srllib.inspect

from _common import *

class _MyClass(object):
    cvar = "cvar"
    
    def __init__(self):
        self.attr = "attr"
    
    def mthd(self):
        pass

class InspectTest(TestCase):
    def test_get_members_instance(self):
        """ Test get_members function on a class instance. """
        obj = _MyClass()
        members = srllib.inspect.get_members(obj)
        expected = {"mthd": obj.mthd, "attr": obj.attr, "cvar": obj.cvar}
        self.__verify(members, expected)
        
    def test_get_members_instance_method(self):
        """ Test getting methods of a class instance. """
        obj = _MyClass()
        members = srllib.inspect.get_members(obj, inspect.isroutine)
        expected = {"mthd": obj.mthd}
        self.__verify(members, expected)
        
    def test_get_members_class(self):
        """ Test get_members on a class. """
        members = srllib.inspect.get_members(_MyClass)
        expected = {"mthd": _MyClass.mthd, "cvar": _MyClass.cvar}        
        self.__verify(members, expected)
    
    def __verify(self, got, expected):
        for k in got.keys():
            if k.startswith("__") and k.endswith("__"):
                got.pop(k)
        self.assertEqual(got, expected,
            "Expected members %r, got %r" % (expected, got))