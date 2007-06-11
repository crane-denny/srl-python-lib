from _common import *

class StatefulSlot(QObject):
    def __init__(self, emitter, signal, slot, extra_args=[]):
        QObject.__init__(self, emitter)
        self.__emitter, self.__slot, self.__extra = emitter, slot, extra_args
        QObject.connect(emitter, SIGNAL(signal), self)

    def __call__(self, *args):
        self.__slot(self.__emitter, extra_args=self.__extra, *args)

class BrowseFileButton(QToolButton):
    """ Standard button for browsing filesystem. """
    def __init__(self, parent=None, tooltip=None):
        QToolButton.__init__(self, parent)
        self.setText("...")
        if tooltip:
            self.setToolTip(tooltip)

class BrowseFile(QWidget):
    """ Widget composed of a QLineEdit and a L{BrowseFileButton} for browsing the filesystem.

    @cvar DefaultBrowseTooltip: Default tooltip for browse button.
    @ivar path_edit: QLineEdit for displaying/entering filepath.
    @ivar: browse_button: L{BrowseFileButton} for opening browse dialog.
    """
    DefaultBrowseTooltip = "Browse for file"

    def __init__(self, parent=None, tooltip=None, browse_tooltip=
            DefaultBrowseTooltip):
        QWidget.__init__(self, parent)

        path_edit, browse_btn = self.path_edit, self.browse_button = \
                QLineEdit(self), BrowseFileButton(self)
        if tooltip:
            path_edit.setToolTip(tooltip)
        if browse_tooltip:
            browse_btn.setToolTip(browse_tooltip)

        lay = QHBoxLayout(self)
        lay.setMargin(0)
        lay.addWidget(path_edit, 1)
        lay.addWidget(browse_btn, 0, Qt.AlignRight)
