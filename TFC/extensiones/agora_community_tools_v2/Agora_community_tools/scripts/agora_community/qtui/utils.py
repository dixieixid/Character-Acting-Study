"""Various utilities for QT UI."""

import os

from ..constants import ICONS_PATH
from . import qt


class SingletonWidgetMeta(type(qt.QWidget)):
    """Create a single instance of a widget."""

    def __call__(cls, *args, **kwargs):
        """Get an existing widget instance or create a new one."""
        if 'parent' in kwargs and isinstance(kwargs['parent'], qt.QWidget):
            instance = findWidgetByClass(cls, parent=kwargs['parent'])
        else:
            instance = findWidgetByClass(cls)

        if instance:
            instance.activateWindow()
            return instance

        return super().__call__(*args, **kwargs)


def loadIcon(name, asPixmap=False):
    """Load an icon from the default icons directory."""
    filename = os.path.join(ICONS_PATH, name)
    extension = '.svg' if not name.endswith(('.svg', '.png')) else ''
    iconPath = filename + extension

    if asPixmap:
        return qt.QPixmap(iconPath)

    return qt.QIcon(iconPath)


def findWidgetByClass(cls, parent=None):
    """Find a widget by its class."""
    if parent:
        return parent.findChild(cls)

    try:
        appWidgets = qt.QApplication.instance().topLevelWidgets()
    except AttributeError:
        # app is a `QCoreApplication` instance (it happens when Maya is opening).
        return None

    for widget in appWidgets:
        if isinstance(widget, cls):
            return widget

    for widget in appWidgets:
        instance = widget.findChild(cls)

        if instance:
            return instance

    return None


def singletonWidget(cls):
    """Class decorator to restrict widgets to only one instance."""
    if isinstance(cls, SingletonWidgetMeta):
        return cls

    return SingletonWidgetMeta(cls.__name__, cls.__bases__, dict(cls.__dict__))
