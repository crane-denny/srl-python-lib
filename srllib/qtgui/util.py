from _common import *

class StatefulSlot(QObject):
    def __init__(self, emitter, signal, slot, extra_args=[]):
        QObject.__init__(self, emitter)
        self.__emitter, self.__slot, self.__extra = emitter, slot, extra_args
        QObject.connect(emitter, SIGNAL(signal), self)

    def __call__(self, *args):
        self.__slot(self.__emitter, extra_args=self.__extra, *args)

class BrowseFileButton(QPushButton):
    """ Standard button for browsing filesystem. """
    def __init__(self, parent):
        QPushButton.__init__(self, "...", parent)
