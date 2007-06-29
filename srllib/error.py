""" Exception classes. """
class SrlError(Exception):
    """ Base SRL exception. """

class BusyError(SrlError):
    """ General indication that an object is busy with an operation. """