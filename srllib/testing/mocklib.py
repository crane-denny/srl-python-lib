""" Library of mock classes. """
from mock import *

class _Singleton(Mock):
    """ Class for the kind of mocks where there should only exist one instance. """
    __theInstance = None

    def __init__(self, *args, **kwds):
        assert self.__class__.__theInstance is None
        Mock.__init__(self, *args, **kwds)
        self.__class__.__theInstance = self

    @classmethod
    def resetSingleton(cls):
        """ Prepare for new test run. """
        cls.__theInstance = None

    @classmethod
    def getInstance(cls):
        return cls.__theInstance

from PyQt4.QtGui import QMessageBox, QFileDialog

class MockQMessageBox(Mock):
    _MockRealClass = QMessageBox

class MockQFileDialog(Mock):
    _MockRealClass = QFileDialog
