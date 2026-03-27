"""Allow Qt UI to be created in a more declarative/tree-like style using context managers."""

import os
import sys

from ..vendor.Qt.QtCore import *
from ..vendor.Qt.QtWidgets import *
from ..vendor.Qt.QtGui import *
from ..vendor.Qt.QtCompat import wrapInstance, loadUi

try:
    SCALE_FACTOR = round(1.0 / float(os.getenv('QT_SCREEN_SCALE_FACTORS', '1.0').split(';')[0]), 2)
except ValueError:
    SCALE_FACTOR = 1.0

_self = sys.modules[__name__]
_activeContainers = []


def _onLayoutEnter(layout):
    if _activeContainers:
        container = _activeContainers[-1]

        if hasattr(container, 'addLayout') and container.layout():
            container.addLayout(layout)
        elif isinstance(container, QWidget):
            container.setLayout(layout)

    _activeContainers.append(layout)

    return layout


def _onWidgetEnter(widget):
    if _activeContainers:
        container = _activeContainers[-1]

        if not isinstance(container, (QFormLayout, QTabWidget)):
            # QFormLayout/QTabWidget uses `addRow/addTab`
            try:
                container.addWidget(widget)
            except AttributeError:
                pass

    _activeContainers.append(widget)

    return widget


def _onExit(*_args):
    _activeContainers.pop(-1)


_QWidget = QWidget
_QLayout = QLayout
_className = _class = None


class _DeclarativeType(type(QObject)):
    def __instancecheck__(cls, instance):
        return issubclass(type(instance), cls)

    def __subclasscheck__(cls, subclass):
        return cls in subclass.__mro__


def _findChildren(self, cls, *args, **kwargs):
    if cls.__name__.startswith('Q'):
        cls = cls.__originalClass__

    return self.__originalClass__.findChildren(self, cls, *args, **kwargs)


for _className, _class in _self.__dict__.items():
    if not isinstance(_class, type) or _className.startswith('_'):
        continue

    if issubclass(_class, _QWidget):
        _self.__dict__[_className] = _DeclarativeType(
            _className,
            (_class,),
            {
                '__originalClass__': _class,
                '__enter__': _onWidgetEnter,
                '__exit__': _onExit,
                'findChildren': _findChildren,
            },
        )
    elif issubclass(_class, _QLayout):
        _self.__dict__[_className] = _DeclarativeType(
            _className,
            (_class,),
            {
                '__originalClass__': _class,
                '__enter__': _onLayoutEnter,
                '__exit__': _onExit,
            },
        )
