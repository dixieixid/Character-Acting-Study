from .. import qt
from ..stylesheet import addStyleClass
from ..utils import loadIcon


class BusyOverlay(qt.QWidget):
    """An overlay to show on top of widgets on slower operations."""

    def __init__(self, parent, autoShow=True):
        super(BusyOverlay, self).__init__(parent)

        self.setAttribute(qt.Qt.WA_StyledBackground)

        layout = qt.QVBoxLayout()
        layout.setAlignment(qt.Qt.AlignCenter)

        spinner = qt.QLabel()
        spinner.setAlignment(qt.Qt.AlignCenter)
        spinner.setPixmap(loadIcon('loader', asPixmap=True).scaled(64, 64))

        message = qt.QLabel('Please wait...')
        message.setAlignment(qt.Qt.AlignCenter)

        layout.addWidget(spinner)
        layout.addWidget(message)

        addStyleClass(self, 'busy-overlay')
        addStyleClass(spinner, 'busy-overlay__spinner')
        addStyleClass(message, 'busy-overlay__message')

        self.setLayout(layout)

        if autoShow:
            self.show()

    def showEvent(self, event):
        """Receive the show event."""
        super(BusyOverlay, self).showEvent(event)

        if self.parent():
            self.resize(self.parent().width(), self.parent().height())

        self.raise_()


class Slider(qt.QWidget):
    """A slider with more options."""

    valueChanged = qt.Signal(float)
    returnPressed = qt.Signal()
    sliderReleased = qt.Signal()

    def __init__(self, minValue, maxValue, defaultValue=None):
        super(Slider, self).__init__()

        addStyleClass(self, 'slider')

        self._min = minValue
        self._max = maxValue
        self._value = minValue
        self._defaultValue = defaultValue if defaultValue is not None else minValue
        self._isFloat = isinstance(minValue, float) or isinstance(maxValue, float)

        self._slider = qt.QSlider(qt.Qt.Horizontal)

        if self._isFloat:
            self._slider.setMinimum(0)
            self._slider.setMaximum(100)
            self._slider.setValue(0)
        else:
            self._slider.setMinimum(minValue)
            self._slider.setMaximum(maxValue)
            self._slider.setValue(minValue)

        self._slider.valueChanged.connect(self._onSliderValueChanged)
        self._slider.sliderReleased.connect(self.sliderReleased.emit)

        self._textField = qt.QLineEdit(str(self._value))

        if self._isFloat:
            textFieldValidator = qt.QDoubleValidator(minValue, maxValue, 3)
            textFieldValidator.setNotation(qt.QDoubleValidator.StandardNotation)
            textFieldValidator.setLocale(qt.QLocale(qt.QLocale.English))
        else:
            textFieldValidator = qt.QIntValidator(minValue, maxValue)

        self._textField.setValidator(textFieldValidator)
        self._textField.textChanged.connect(self._onTextFieldChanged)
        self._textField.returnPressed.connect(self._onReturnPressed)

        layout = qt.QHBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self._textField, 1)
        layout.addWidget(self._slider, 3)

        if defaultValue is not None:
            self.setValue(defaultValue)

            resetButton = qt.QPushButton()
            resetButton.setIcon(loadIcon('undo'))
            resetButton.clicked.connect(self._onResetValue)

            addStyleClass(resetButton, 'slider__reset-button')

            layout.addWidget(resetButton)

        self.setLayout(layout)

    def value(self):
        """Retrieve the current value."""
        return self._value

    def setValue(self, value):
        """Change the current value."""
        self._value = value

        self._updateSliderValue()
        self._updateTextValue()

    def _updateSliderValue(self):
        if self._isFloat:
            sliderValue = (self._value - self._min) / (self._max - self._min) * 100.0
        else:
            sliderValue = self._value

        self._slider.blockSignals(True)
        self._slider.setValue(sliderValue)
        self._slider.blockSignals(False)

    def _updateTextValue(self):
        self._textField.blockSignals(True)
        self._textField.setText(str(round(self._value, 3)))
        self._textField.blockSignals(False)

    def _onSliderValueChanged(self, value):
        if self._isFloat:
            self._value = round(self._min + (self._max - self._min) * (value / 100.0), 3)
        else:
            self._value = value

        self._updateTextValue()

        self.valueChanged.emit(self._value)

    def _onTextFieldChanged(self):
        textValue = self._textField.text()
        self._value = float(textValue) if self._isFloat else int(textValue)

        self._updateSliderValue()

        self.valueChanged.emit(self._value)

    def _onResetValue(self):
        self._value = self._defaultValue

        self._updateSliderValue()
        self._updateTextValue()

        self.valueChanged.emit(self._value)

    def _onReturnPressed(self):
        self._onTextFieldChanged()
        self.returnPressed.emit()


class LayoutSeparator(qt.QWidget):
    """Create a line to separate the widgets in a layout."""

    def __init__(self, horizontal=True):
        super(LayoutSeparator, self).__init__()

        addStyleClass(self, 'layout-separator')
        self.setAttribute(qt.Qt.WA_StyledBackground)

        if horizontal:
            addStyleClass(self, 'layout-separator--horizontal')
            self.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Minimum)
        else:
            addStyleClass(self, 'layout-separator--vertical')
            self.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Minimum)
