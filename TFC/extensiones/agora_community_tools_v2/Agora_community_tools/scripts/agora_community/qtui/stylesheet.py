"""Various stylesheet utilities for QT."""

import os
import re

from . import qssx
from .qt import SCALE_FACTOR


def addWidgetsStyleSheet(widget):
    """Load the custom widgets' style sheet."""
    style_path = os.path.join(os.path.dirname(__file__), '_resources', 'widgets.qss')

    addStyleSheet(widget, style_path)


def addStyleSheet(widget, path, variables=None):
    """Load a new style sheet on top of the existing styles."""
    variables = variables or {}

    if 'SCALE_FACTOR' not in variables:
        variables['SCALE_FACTOR'] = SCALE_FACTOR

    with open(path) as style_file:
        style_data = style_file.read()
        style_data = qssx.parse(style_data, variables)

        widget.setStyleSheet(widget.styleSheet() + style_data)


def addStyleClass(widget, className):
    """Add a style sheet class name to the widget."""
    classProperty = widget.property('class') or ''
    classList = re.split(r'\s+', classProperty.strip())

    for name in re.split(r'\s+', className.strip()):
        if name not in classList:
            classList.append(name)

    widget.setProperty('class', ' '.join(classList))
    widget.setStyleSheet(widget.styleSheet())  # refresh


def removeStyleClass(widget, className):
    """Remove a style sheet class name from the widget."""
    classProperty = widget.property('class') or ''
    classList = re.split(r'\s+', classProperty.strip())

    for name in re.split(r'\s+', className.strip()):
        if name in classList:
            classList.remove(name)

    widget.setProperty('class', ' '.join(classList))
    widget.setStyleSheet(widget.styleSheet())  # refresh


def getStyleClass(widget):
    """Return the style sheet class for the widget."""
    return widget.property('class') or ''
