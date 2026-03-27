"""Custom widgets for creating windows."""

from .. import qt
from ..stylesheet import addWidgetsStyleSheet


class Window(qt.QWidget):
    """Base window."""

    def __init__(self, title='', parent=None):
        super().__init__(parent=parent)

        self.setAttribute(qt.Qt.WA_DeleteOnClose)
        self.setWindowFlags(qt.Qt.Window)
        self.setWindowTitle(title)

        addWidgetsStyleSheet(self)
