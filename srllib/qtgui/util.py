from _common import *
import srllib.qtgui

class BrowseFileButton(QToolButton):
    """ Standard button for browsing filesystem. """
    def __init__(self, parent=None, tooltip=None):
        QToolButton.__init__(self, parent)
        self.setText("...")
        if tooltip:
            self.setToolTip(tooltip)

class _BrowseHelper(object):
    def __init__(self, readonly=False, path=None, tooltip=None):
        if readonly:
            self.path_edit.setReadOnly(True)
        self.__tooltip = tooltip
        if path is not None:
            self.setPath(path)
        if tooltip:
            path_edit.setToolTip(tooltip)

    def setPath(self, path):
        """Set filepath."""
        self.path_edit.setText(path)

class _Browse(QWidget, _BrowseHelper):
    def __init__(self, parent, tooltip, browse_tooltip, readonly, path):
        QWidget.__init__(self, parent)

        path_edit, browse_btn = self.path_edit, self.browse_button = \
                QLineEdit(self), BrowseFileButton(self)
        if browse_tooltip:
            browse_btn.setToolTip(browse_tooltip)

        lay = QHBoxLayout(self)
        lay.setMargin(0)
        lay.addWidget(path_edit, 1)
        lay.addWidget(browse_btn, 0, Qt.AlignRight)

        QObject.connect(browse_btn, SIGNAL("clicked()"), self.__slot_browse)

        _BrowseHelper.__init__(self, readonly, path, tooltip)

    def __slot_browse(self):
        fpath = self._get_filepath()
        if fpath is not None:
            self.setPath(QDir.toNativeSeparators(fpath))

class BrowseFile(_Browse):
    """ Widget composed of a QLineEdit and a L{BrowseFileButton} for browsing
    for a file.

    @cvar DefaultBrowseTooltip: Default tooltip for browse button.
    @ivar path_edit: QLineEdit for displaying/entering filepath.
    @ivar browse_button: L{BrowseFileButton} for opening browse dialog.
    """
    DefaultBrowseTooltip = "Browse for file"

    def __init__(self, parent=None, tooltip=None, browse_tooltip=DefaultBrowseTooltip,
            filter=None, readonly=False, path=None):
        """
        @param tooltip: Optionally specify tooltip for line edit.
        @param browse_tooltip: Optionally specify tooltip for browse button.
        @param filter: Optionally specify a file filter (as a string, e.g.,
        "Images (*.png *.jpg)".
        @param readonly: Make line edit read-only?
        @param path: Optional initial path.
        """
        _Browse.__init__(self, parent, tooltip, browse_tooltip, readonly, path)

        self.__filter = filter or QString()

    def _get_filepath(self):
        fpath = QFileDialog.getOpenFileName(self, "Open File", QString(),
                self.__filter)
        if not fpath.isNull():
            return fpath
        return None

class BrowseDirectory(_Browse):
    """ Widget composed of a QLineEdit and a L{BrowseFileButton} for browsing
    for a directory.

    @cvar DefaultBrowseTooltip: Default tooltip for browse button.
    @ivar path_edit: QLineEdit for displaying/entering filepath.
    @ivar browse_button: L{BrowseFileButton} for opening browse dialog.
    """
    DefaultBrowseTooltip = "Browse for directory"

    def __init__(self, parent=None, tooltip=None, browse_tooltip=DefaultBrowseTooltip,
            readonly=False, path=None):
        """
        @param tooltip: Optionally specify tooltip for line edit.
        @param browse_tooltip: Optionally specify tooltip for browse button.
        @param readonly: Make line edit read-only?
        @param path: Optional initial path.
        """
        _Browse.__init__(self, parent, tooltip, browse_tooltip, readonly, path)

    def _get_filepath(self):
        fpath = QFileDialog.getExistingDirectory(self, "Open Directory", QString())
        if not fpath.isNull():
            return fpath
        return None

class UndoStack(QtGui.QUndoStack):
    """ Specialization of QUndoStack).

    @ivar is_enabled: Enable pushing of commands? If disabled, commands are only
    performed, not pushed on the stack. Useful for modes when the undo stack
    shouldn't be updated.
    """
    __super = QtGui.QUndoStack

    def __init__(self, enable=True, parent=None):
        self.__super.__init__(self, parent)
        self.is_enabled = enable

    def push(self, command):
        if self.is_enabled:
            self.__super.push(self, command)
        else:
            command.redo()

def Action(text, slot=None, icon=None, shortcut=None, parent=None):
    """ Create a QAction.
    """
    if icon is not None:
        icon = QtGui.QIcon(icon)
    action = QtGui.QAction(icon, text, parent)
    if shortcut is not None:
        action.setShortcut(shortcut)
    if slot is not None:
        srllib.qtgui.connect(action, "triggered()", slot)
    return action
