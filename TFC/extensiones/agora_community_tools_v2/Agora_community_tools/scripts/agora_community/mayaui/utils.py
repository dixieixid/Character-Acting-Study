"""Utility UI functions."""

import os

from maya import OpenMayaUI as omui

from agora_community import qtui


def addBaseStyleSheet(widget):
    """Load the base style sheet."""
    style_path = os.path.join(os.path.dirname(__file__), '_resources', 'base.qss')

    qtui.addStyleSheet(widget, style_path)


def mayaMainWindow():
    """Retrieve the Maya's main window as `QMainWindow`."""
    mainWindowPtr = omui.MQtUtil.mainWindow()

    return qtui.wrapInstance(int(mainWindowPtr), qtui.QMainWindow)


def addWidgetToMayaLayout(widgetName, parentName, keepOriginalName=False):
    """Add a widget to an existing Maya layout.

    Maya may modify the widget's name to ensure uniqueness.
    To avoid this set `keepOriginalName` to `True`.
    """
    widgetPtr = omui.MQtUtil.findControl(widgetName)
    parentPtr = omui.MQtUtil.findControl(parentName)

    omui.MQtUtil.addWidgetToMayaLayout(int(widgetPtr), int(parentPtr))

    if keepOriginalName:
        # MQtUtil.addWidgetToMayaLayout may modify the objectName to ensure uniqueness.
        widget = qtui.wrapInstance(int(widgetPtr), qtui.QWidget)
        widget.setObjectName(widgetName)
