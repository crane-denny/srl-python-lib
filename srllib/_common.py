"""Shared stuff.

@var logger: The srllib L{logger<logging.Logger>}.
"""
import logging
import platform

__all__ = ["get_os", "get_os_name", "get_os_version", "Os_Linux",
    "Os_Windows", "logger"]


class _NullHandler(logging.Handler):
    """Default do-nothing logging handler.

    Since this is a library, we want to swallow log messages, unless the
    application has enabled logging.
    """
    def emit(self, record):
        """Swallow message."""

logger = logging.getLogger("srllib")
# Swallow log messages emanating from this library by default
# It should be up to applications to enable logging
logger.handlers = [_NullHandler()]

#{ Operating-system logic

Os_Linux = "linux"
Os_Windows = "windows"
Os_Mac = "darwin"
Os_Solaris = "sunos"

OsCollection_Posix = (Os_Linux, Os_Mac, Os_Solaris)
Os_Posix = OsCollection_Posix   # Backwards-compat

def get_os():
    """ Get the current operating system.

    Lower-case strings are used to identify operating systems.
    @return: A pair of OS identifier and OS release (e.g. "xp") strings.
    """
    name, host, rls, ver, mach, proc = platform.uname()
    name = name.lower()
    if name == "microsoft":
        # On some Windows versions, it comes out on a different form than usual
        name = rls.lower()
        rls = ver

    return name, rls

def get_os_name():
    """ Get the name of the current operating system.

    This convenience function simply returns the first element of the tuple
    returned by L{get_os}.
    """
    return get_os()[0]

def get_os_version():
    """ Get the version of the current operating system.

    This convenience function simply returns the second element of the tuple
    returned by L{get_os}.
    """
    return get_os()[1]

#}
