from srllib._common import (get_os, get_os_name, get_os_version, Os_Linux,
        Os_Windows, Os_Mac, OsCollection_Posix)
from srllib.testing import *


def only_posix(func):
    """Decorator for tests that are particular to POSIX."""
    if get_os_name() in OsCollection_Posix:
        return func
    return None

def only_windows(func):
    """Decorator for tests that are particular to Windows."""
    if get_os_name() == Os_Windows:
        return func
    return None
