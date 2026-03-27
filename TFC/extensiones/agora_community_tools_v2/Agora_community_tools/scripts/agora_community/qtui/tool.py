from ..constants import DOCS_URL
from . import qt
from .widgets import Window


class ToolWindow(Window):
    """Base window class for all tools."""

    def __init__(self, title='', parent=None):
        super().__init__(title, parent)

        self.__menuBarLayout = qt.QHBoxLayout()
        self.__menuBarLayout.setAlignment(qt.Qt.AlignLeft)
        self.__menuBarLayout.setContentsMargins(0, 0, 0, 0)
        self.__menuBarLayout.setSpacing(0)

        self.__menuBar = qt.QMenuBar(self)
        self.__menuBarLayout.addWidget(self.__menuBar)

        self.onMenuBar(self.__menuBar)

        helpMenu = self.__menuBar.addMenu('Help')
        helpMenu.addAction('Documentation', lambda: qt.QDesktopServices.openUrl(DOCS_URL))

        self.__mainLayout = qt.QVBoxLayout()
        self.__mainLayout.setAlignment(qt.Qt.AlignTop)
        self.__mainLayout.setContentsMargins(0, 0, 0, 0)
        self.__mainLayout.setSpacing(0)

        self.__contentLayout = qt.QVBoxLayout()
        self.__contentLayout.setAlignment(qt.Qt.AlignTop)
        self.__contentLayout.setContentsMargins(
            4 * qt.SCALE_FACTOR,
            2,
            4 * qt.SCALE_FACTOR,
            4 * qt.SCALE_FACTOR,
        )
        self.__contentLayout.setSpacing(2 * qt.SCALE_FACTOR)

        self.__mainLayout.addLayout(self.__menuBarLayout)
        self.__mainLayout.addLayout(self.__contentLayout)

        self.setLayout(self.__mainLayout)

    def layout(self):
        """Retrieve the content layout."""
        return self.__contentLayout

    def menuBarLayout(self):
        """Retrieve the menu bar layout."""
        return self.__menuBarLayout

    def onMenuBar(self, menuBar):
        """Add menus to menu bar."""
