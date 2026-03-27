"""Custom widgets that contain other widgets."""

from .. import qt
from ..stylesheet import addStyleClass
from ..utils import loadIcon


class ScrollBox(qt.QScrollArea):
    """Create a scrollable box area."""

    def __init__(self, boxLayout):
        super(ScrollBox, self).__init__()

        boxLayout.setContentsMargins(0, 0, 0, 0)

        self._container = qt.QWidget()
        self._container.setLayout(boxLayout)

        addStyleClass(self, 'scroll-box')
        addStyleClass(self._container, 'scroll-box__container')

        self.setWidget(self._container)
        self.setWidgetResizable(True)
        self.setFocusPolicy(qt.Qt.NoFocus)

    def addWidget(self, widget):
        """Add widget to the end of the layout."""
        self._container.layout().addWidget(widget)

    def removeWidget(self, widget):
        """Remove widget from the layout."""
        self._container.layout().removeWidget(widget)

    def insertWidget(self, index, widget):
        """Insert widget at position index."""
        self._container.layout().insertWidget(index, widget)

    def addLayout(self, layout):
        """Add layout to the end of the main layout."""
        self._container.layout().addLayout(layout)

    def layout(self):
        """Return the used `QLayout`."""
        return self._container.layout()

    def container(self):
        """Return the container."""
        return self._container


class ScrollHBox(ScrollBox):
    """Create a scrollable horizontal box area."""

    def __init__(self):
        boxLayout = qt.QHBoxLayout()
        boxLayout.setAlignment(qt.Qt.AlignLeft)

        super(ScrollHBox, self).__init__(boxLayout)

        self.setVerticalScrollBarPolicy(qt.Qt.ScrollBarAlwaysOff)


class ScrollVBox(ScrollBox):
    """Create a scrollable vertical box area."""

    def __init__(self):
        boxLayout = qt.QVBoxLayout()
        boxLayout.setAlignment(qt.Qt.AlignTop)

        super(ScrollVBox, self).__init__(boxLayout)

        self.setHorizontalScrollBarPolicy(qt.Qt.ScrollBarAlwaysOff)


class GroupBox(qt.QWidget):
    """Create a box area that can be collapsed."""

    collapseToggled = qt.Signal(bool)
    menuAboutToShow = qt.Signal(qt.QMenu)

    def __init__(
        self,
        title='',
        icon=None,
        collapsable=True,
        collapsed=False,
        checkable=False,
        hasMenu=False,
        uncheckedOpacity=1.0,
    ):
        super(GroupBox, self).__init__()

        self._collapsable = collapsable
        self._uncheckedOpacity = uncheckedOpacity

        addStyleClass(self, 'group-box')

        self._mainLayout = qt.QVBoxLayout()
        self._mainLayout.setContentsMargins(0, 0, 0, 0)
        self._mainLayout.setSpacing(0)

        super(GroupBox, self).setLayout(self._mainLayout)

        self._titleBar = qt.QWidget()
        addStyleClass(self._titleBar, 'group-box__title-bar')

        self._contentBox = qt.QWidget()
        addStyleClass(self._contentBox, 'group-box__content-box')

        self._mainLayout.addWidget(self._titleBar)
        self._mainLayout.addWidget(self._contentBox)

        self._titleBarLabel = qt.QPushButton(title)
        addStyleClass(self._titleBarLabel, 'group-box__title-label')

        self._buttonsBarLayout = qt.QHBoxLayout()
        self._buttonsBarLayout.setContentsMargins(4, 0, 0, 0)
        self._buttonsBarLayout.setSpacing(0)
        self._buttonsBar = qt.QWidget()
        self._buttonsBar.setLayout(self._buttonsBarLayout)
        addStyleClass(self._buttonsBar, 'group-box__buttons-bar')

        titleBarLayout = qt.QHBoxLayout()
        titleBarLayout.setContentsMargins(0, 0, 0, 0)
        titleBarLayout.setSpacing(0)
        titleBarLayout.addWidget(self._titleBarLabel, 1)
        titleBarLayout.addWidget(self._buttonsBar)
        self._titleBar.setLayout(titleBarLayout)

        if icon:
            iconWidget = qt.QPushButton()
            iconWidget.setIcon(icon)
            titleBarLayout.insertWidget(0, iconWidget)
            addStyleClass(iconWidget, 'group-box__title-icon')
            addStyleClass(self._titleBar, 'group-box__title-bar--with-icon')

        if collapsable:
            self._collapseTrigger = qt.QPushButton()

            self._collapseTrigger.clicked.connect(self._onCollapseToggle)
            self._titleBarLabel.clicked.connect(self._onCollapseToggle)
            if icon:
                iconWidget.clicked.connect(self._onCollapseToggle)

            titleBarLayout.insertWidget(0, self._collapseTrigger)

            addStyleClass(self._collapseTrigger, 'group-box__collapse-trigger')
            addStyleClass(self._titleBar, 'group-box__title-bar--collapsable')

            self.collapse(collapsed)

        if checkable:
            self._checkbox = qt.QCheckBox()
            self._checkbox.stateChanged.connect(self._onChecked)

            titleBarLayout.insertWidget(0, self._checkbox)

            addStyleClass(self._checkbox, 'group-box__checkbox')

            self._onChecked()
        else:
            self._checkbox = None

        if hasMenu:
            self._menu = qt.QMenu(self)
            self._titleBarLabel.contextMenuEvent = self._onShowMenu

    def setTitle(self, title):
        """Set the box title."""
        self._titleBarLabel.setText(title)

    def layout(self):
        """Return the box layout."""
        return self._contentBox.layout()

    def setLayout(self, layout):
        """Set the box layout."""
        self._contentBox.setLayout(layout)

    def addLayout(self, layout):
        """Add inner layout to the end of the main layout."""
        self.layout().addLayout(layout)

    def addWidget(self, widget):
        """Add widget to the end of the layout."""
        self.layout().addWidget(widget)

    def insertWidget(self, index, widget):
        """Insert a widget at the given index."""
        self.layout().insertWidget(index, widget)

    def titleBar(self):
        """Return the widget for the title bar."""
        return self._titleBar

    def titleBarLabel(self):
        """Return the widget for the title bar label."""
        return self._titleBarLabel

    def checkbox(self):
        """Return the checkbox."""
        return self._checkbox

    def buttonsBar(self):
        """Return the buttons bar."""
        return self._buttonsBarLayout

    def contentBox(self):
        """Return the content box."""
        return self._contentBox

    def collapse(self, collapse=None):
        """Hide/show content."""
        if collapse or collapse is None:
            self._contentBox.hide()
        else:
            self._contentBox.show()

        self.updateGeometry()

        self._updateIcon()

    def isCollapsed(self):
        """Check if content is hidden."""
        return self._contentBox.isHidden()

    def _onCollapseToggle(self):
        collapsed = not self.isCollapsed()

        self.collapse(collapsed)

        self.collapseToggled.emit(collapsed)

    def _updateIcon(self):
        if self._contentBox.isHidden():
            icon = 'caret-right'
        else:
            icon = 'caret-down'

        if self._collapsable:
            self._collapseTrigger.setIcon(loadIcon(icon))

    def _onShowMenu(self, event):
        self.menuAboutToShow.emit(self._menu)
        self._menu.exec_(event.globalPos())

    def _onChecked(self):
        if self._checkbox.isChecked():
            self.setGraphicsEffect(None)
        elif self._uncheckedOpacity < 1.0:
            opacityEffect = qt.QGraphicsOpacityEffect(self)
            opacityEffect.setOpacity(self._uncheckedOpacity)

            self.setGraphicsEffect(opacityEffect)


class GroupHBox(GroupBox):
    """Create a horizontal box area that can be collapsed."""

    def __init__(
        self,
        title='',
        icon=None,
        collapsable=True,
        collapsed=False,
        checkable=False,
        hasMenu=False,
        uncheckedOpacity=1.0,
    ):
        super(GroupHBox, self).__init__(
            title,
            icon,
            collapsable,
            collapsed,
            checkable,
            hasMenu,
            uncheckedOpacity,
        )

        layout = qt.QHBoxLayout()

        self.setLayout(layout)


class GroupVBox(GroupBox):
    """Create a vertical box area that can be collapsed."""

    def __init__(
        self,
        title='',
        icon=None,
        collapsable=True,
        collapsed=False,
        checkable=False,
        hasMenu=False,
        uncheckedOpacity=1.0,
    ):
        super(GroupVBox, self).__init__(
            title,
            icon,
            collapsable,
            collapsed,
            checkable,
            hasMenu,
            uncheckedOpacity,
        )

        layout = qt.QVBoxLayout()
        layout.setAlignment(qt.Qt.AlignTop)

        self.setLayout(layout)


class PopupPanel(qt.QWidget):
    """A floating widget."""

    class Alignment:
        LEFT = 1
        RIGHT = 2
        TOP = 3
        BOTTOM = 4

    closed = qt.Signal()

    def __init__(self, parent=None):
        super(PopupPanel, self).__init__(parent)

        self.setAttribute(qt.Qt.WA_DeleteOnClose)
        self.setAttribute(qt.Qt.WA_StyledBackground)
        self.setWindowFlags(qt.Qt.Popup)

        addStyleClass(self, 'popup-panel')

    @classmethod
    def open(cls, targetWidget, contentCreator, alignment=Alignment.BOTTOM):
        """Create a popop and show it."""
        popup = PopupPanel(targetWidget)
        contentWidget = contentCreator(popup)

        layout = qt.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(contentWidget)

        popup.setLayout(layout)
        popup.show(targetWidget, alignment)

    def show(self, widget, alignment=Alignment.BOTTOM):
        """Show the popup near the provided widget."""
        super(PopupPanel, self).show()

        self.move(self._findOptimalPosition(widget, alignment))

    def closeEvent(self, event):
        """Call when Qt receives a window close request."""
        super(PopupPanel, self).closeEvent(event)

        self.closed.emit()

    def _findOptimalPosition(self, widget, preferredAlignment):
        screenRect = qt.QApplication.screenAt(widget.mapToGlobal(qt.QPoint())).geometry()
        popupRect = qt.QRect(0, 0, self.width(), self.height())

        alignments = [preferredAlignment]

        if preferredAlignment is self.Alignment.LEFT:
            alignments.append(self.Alignment.RIGHT)
            alignments.append(self.Alignment.TOP)
            alignments.append(self.Alignment.BOTTOM)

        if preferredAlignment is self.Alignment.RIGHT:
            alignments.append(self.Alignment.LEFT)
            alignments.append(self.Alignment.TOP)
            alignments.append(self.Alignment.BOTTOM)

        if preferredAlignment is self.Alignment.TOP:
            alignments.append(self.Alignment.BOTTOM)
            alignments.append(self.Alignment.LEFT)
            alignments.append(self.Alignment.RIGHT)

        if preferredAlignment is self.Alignment.BOTTOM:
            alignments.append(self.Alignment.TOP)
            alignments.append(self.Alignment.LEFT)
            alignments.append(self.Alignment.RIGHT)

        for alignment in alignments:
            popupRect.moveTo(self._findPosition(widget, alignment))

            if screenRect.contains(popupRect):
                return popupRect.topLeft()

            if alignment is self.Alignment.TOP or alignment is self.Alignment.BOTTOM:
                if popupRect.x() < screenRect.x():
                    popupRect.moveLeft(screenRect.x())
                else:
                    popupRect.moveLeft(popupRect.x() - (popupRect.right() - screenRect.right()))
            elif alignment is self.Alignment.LEFT or alignment is self.Alignment.RIGHT:
                if popupRect.y() < screenRect.y():
                    popupRect.moveTop(screenRect.y())
                else:
                    popupRect.moveTop(popupRect.y() - (popupRect.bottom() - screenRect.bottom()))

            if screenRect.contains(popupRect):
                return popupRect.topLeft()

        return popupRect.topLeft()

    def _findPosition(self, widget, alignment):
        position = widget.mapToGlobal(qt.QPoint(0, 0))

        if alignment is self.Alignment.LEFT:
            return qt.QPoint(
                position.x() - self.width(),
                position.y() - self.height() / 2 + widget.height() / 2,
            )

        if alignment is self.Alignment.RIGHT:
            return qt.QPoint(
                position.x() + widget.width(),
                position.y() - self.height() / 2 + widget.height() / 2,
            )

        if alignment is self.Alignment.TOP:
            return qt.QPoint(
                position.x() - self.width() / 2 + widget.width() / 2,
                position.y() - self.height(),
            )

        return qt.QPoint(
            position.x() - self.width() / 2 + widget.width() / 2,
            position.y() + widget.height(),
        )
