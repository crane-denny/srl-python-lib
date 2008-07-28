""" Test the mock module. """
from srllib.testing.mock import Mock, MockInterfaceError

from _common import *

class _Mocked(object):
    @property
    def prop(self):
        return "prop"

class Mocker(Mock):
    _MockRealClass = _Mocked
    
    @property
    def prop(self):
        pass

class InterfaceTest(TestCase):
    """ Verify interface checking of Mock.
    """
    def test_properties_invalid(self):
        """ Verify that an invalid property is caught.
        """
        class Mocker(Mock):
            _MockRealClass = _Mocked
            
            @property
            def prop(self):
                pass
            
            @property
            def invalidprop(self):
                pass
            
        self.assertRaises(MockInterfaceError, Mocker)
    
    def test_properties_valid(self):
        """ Verify that valid properties pass.
        """ 
        Mocker()
    