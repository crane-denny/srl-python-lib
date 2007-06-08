""" Utilities for use with PyQt4 """
from _application import *
from _common import *

def get_app():
    """ Get the current L{Application} instance. """
    return Application.the_app
