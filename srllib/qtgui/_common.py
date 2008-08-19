from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import *
from PyQt4.QtGui import *

def message_critical(title, text, detailed_text=None, informative_text=None,
    parent=None):
    """ Display a critical message in a L{QMessageBox}. """
    dlg = QMessageBox(QMessageBox.Critical, title, text, QMessageBox.Ok, parent)
    if informative_text:
        dlg.setInformativeText(informative_text)
    if detailed_text:
        dlg.setDetailedText(detailed_text)
    dlg.exec_()

def message_warning(title, text, detailed_text=None, informative_text=None,
    parent=None):
    """ Display a warning message in a L{QMessageBox}. """
    dlg = QMessageBox(QMessageBox.Warning, title, text, QMessageBox.Ok, parent)
    if informative_text:
        dlg.setInformativeText(informative_text)
    if detailed_text:
        dlg.setDetailedText(detailed_text)
    dlg.exec_()
