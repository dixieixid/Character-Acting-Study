"""Custom buttons."""

from .. import qt
from ..stylesheet import addStyleClass, removeStyleClass
from ..utils import loadIcon


class IconButton(qt.QPushButton):
    """Create a button with an icon loaded from default icons location."""

    def __init__(self, icon='', parent=None):
        super().__init__(parent)

        addStyleClass(self, 'icon-button')

        if icon:
            self.setIcon(icon)

    def setIcon(self, icon):
        """Set the icon."""
        if isinstance(icon, str):
            icon = loadIcon(icon)

        super().setIcon(icon)


class TintedIconButton(qt.QPushButton):
    """A button with the icon's color changeable from QSS.

    Available QSS properties:
        - qproperty-tint
        - qproperty-tintHover
        - qproperty-tintPressed
    """

    def __init__(self, *args, **kwargs):
        super(TintedIconButton, self).__init__(*args, **kwargs)

        self._tint = ''
        self._tintHover = ''
        self._tintPressed = ''

        self._normalIcon = self.icon()
        self._hoverIcon = None
        self._pressedIcon = None

        self._hovered = False

    def getTint(self):
        """Retrieve the tint color."""
        return self._tint

    def setTint(self, value):
        """Change the tint color."""
        self._tint = value

        if self._normalIcon and value:
            self._normalIcon = self._changeIconColor(self._normalIcon, value)

            super(TintedIconButton, self).setIcon(self._normalIcon)

    def getTintHover(self):
        """Retrieve the tint color for hover state."""
        return self._tintHover

    def setTintHover(self, value):
        """Change the tint color for hover state."""
        self._tintHover = value

        if self._normalIcon and value:
            self._hoverIcon = self._changeIconColor(self._normalIcon, value)
        else:
            self._hoverIcon = None

    def getTintPressed(self):
        """Retrieve the tint color for pressed state."""
        return self._tintPressed

    def setTintPressed(self, value):
        """Change the tint color for pressed state."""
        self._tintPressed = value

        if self._normalIcon and value:
            self._pressedIcon = self._changeIconColor(self._normalIcon, value)
        else:
            self._pressedIcon = None

    def setIcon(self, icon):
        """Change the icon."""
        if icon and self.tint:
            self._normalIcon = self._changeIconColor(icon, self.tint)
        else:
            self._normalIcon = icon

        if icon and self.tintHover:
            self._hoverIcon = self._changeIconColor(icon, self.tintHover)
        else:
            self._hoverIcon = None

        if icon and self.tintPressed:
            self._pressedIcon = self._changeIconColor(icon, self.tintPressed)
        else:
            self._pressedIcon = None

        super(TintedIconButton, self).setIcon(self._normalIcon)

    def enterEvent(self, event):
        """Receive mouse enter event."""
        super(TintedIconButton, self).enterEvent(event)

        if self._hoverIcon:
            super(TintedIconButton, self).setIcon(self._hoverIcon)

        self._hovered = True

    def leaveEvent(self, event):
        """Receive mouse leave event."""
        super(TintedIconButton, self).leaveEvent(event)

        if self._normalIcon:
            super(TintedIconButton, self).setIcon(self._normalIcon)

        self._hovered = False

    def mousePressEvent(self, event):
        """Receive mouse press event."""
        super(TintedIconButton, self).mousePressEvent(event)

        if self._pressedIcon:
            super(TintedIconButton, self).setIcon(self._pressedIcon)

    def mouseReleaseEvent(self, event):
        """Receive mouse release event."""
        super(TintedIconButton, self).mouseReleaseEvent(event)

        if self._hovered and self._hoverIcon:
            super(TintedIconButton, self).setIcon(self._hoverIcon)
        elif self._normalIcon:
            super(TintedIconButton, self).setIcon(self._normalIcon)

    @staticmethod
    def _changeIconColor(icon, color):
        if not isinstance(color, qt.QColor):
            color = qt.QColor(color)

        pixmap = icon.pixmap(1000, 1000)
        mask = pixmap.createMaskFromColor(qt.Qt.transparent, qt.Qt.MaskInColor)

        pixmap.fill(color)
        pixmap.setMask(mask)

        return qt.QIcon(pixmap)

    tint = qt.Property(str, getTint, setTint)
    tintHover = qt.Property(str, getTintHover, setTintHover)
    tintPressed = qt.Property(str, getTintPressed, setTintPressed)


class ToggleButton(qt.QWidget):
    """Toggle button with multi-state."""

    stateChanged = qt.Signal(object)

    def __init__(self, buttonClass=qt.QPushButton):
        super(ToggleButton, self).__init__()

        self.setAttribute(qt.Qt.WA_StyledBackground)

        self._buttonClass = buttonClass
        self._buttons = []
        self._values = []

        self._activeBtn = None
        self._activeValue = None

        addStyleClass(self, 'toggle-button')

        layout = qt.QHBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

    def addState(self, label, value):
        """Add a state."""
        btn = self._buttonClass(label)
        btn.clicked.connect(lambda: self._onStateChange(value))

        addStyleClass(btn, 'toggle-button__button')

        if not self._buttons:
            addStyleClass(btn, 'toggle-button__button--first')

        if self._buttons:
            removeStyleClass(self._buttons[-1], 'toggle-button__button--last')

        if len(self._buttons) > 1:
            addStyleClass(self._buttons[-1], 'toggle-button__button--middle')

        addStyleClass(btn, 'toggle-button__button--last')

        self._buttons.append(btn)
        self._values.append(value)

        self.layout().addWidget(btn)

        if not self._activeValue:
            self.setState(value)

        return btn

    def state(self):
        """Get active state."""
        return self._activeValue

    def setState(self, value):
        """Set active state."""
        try:
            btn = self._buttons[self._values.index(value)]
        except ValueError:
            raise Exception('Toggle Button: Invalid state value: {}'.format(value))

        for stateBtn in self._buttons:
            removeStyleClass(stateBtn, 'toggle-button__button--active')

        addStyleClass(btn, 'toggle-button__button--active')

        self._activeBtn = btn
        self._activeValue = value

    def button(self, stateValue):
        """Retrieve the button associated with the provided state value."""
        return self._buttons[self._values.index(stateValue)]

    def _onStateChange(self, value):
        self.setState(value)

        self.stateChanged.emit(value)


class MenuButton(IconButton):
    """A push button that opens a menu when clicked."""

    menuAboutToShow = qt.Signal(qt.QMenu)

    def __init__(self, icon='bars'):
        super(MenuButton, self).__init__(icon)

        addStyleClass(self, 'menu-button')

        self._menu = qt.QMenu(self)
        self._menu.aboutToShow.connect(lambda: self.menuAboutToShow.emit(self._menu))

        self.setMenu(self._menu)


class ContextMenuButton(qt.QPushButton):
    """A button which shows the menu on right click."""

    def __init__(self, text='', icon='', parent=None):
        super(ContextMenuButton, self).__init__(text=text, parent=parent)

        self._menu = None
        self._menuIndicator = qt.QWidget(self)

        addStyleClass(self, 'context-menu-button')
        addStyleClass(self._menuIndicator, 'context-menu-button__indicator')

        if icon:
            self.setIcon(icon)

            addStyleClass(self, 'context-menu-button--with-icon icon-button')

    def resizeEvent(self, event):
        """Receive resize event."""
        super(ContextMenuButton, self).resizeEvent(event)

        self._menuIndicator.move(
            self.width() - self._menuIndicator.width(),
            self.height() - self._menuIndicator.height(),
        )

    def changeEvent(self, event):
        """Receive change event."""
        super(ContextMenuButton, self).changeEvent(event)

        if event.type() == qt.QEvent.EnabledChange:
            if self.isEnabled():
                removeStyleClass(self._menuIndicator, 'context-menu-button__indicator--disabled')
            else:
                addStyleClass(self._menuIndicator, 'context-menu-button__indicator--disabled')

    def setMenu(self, menu):
        """Set the context menu."""
        self._menu = menu

    def setIcon(self, icon):
        """Set the icon."""
        if isinstance(icon, str):
            icon = loadIcon(icon)

        super().setIcon(icon)

    def contextMenuEvent(self, event):
        """Receive the context menu event."""
        super(ContextMenuButton, self).contextMenuEvent(event)

        if self._menu:
            self._menu.exec_(qt.QCursor.pos())
            self.update()
