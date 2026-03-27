from .databinding import (
    BindableData,
    bind,
    bind_activation,
    bind_creation,
    bind_visibility,
    bind_invisibility,
    bind_callback,
    unbind_callback,
    register_widget,
)

from .qt import *
from .dialogs import *
from .widgets import *
from .stylesheet import *
from .utils import (
    singletonWidget,
    findWidgetByClass,
    loadIcon,
)

from .tool import ToolWindow


# Register the custom widgets for data binding.
register_widget(ToggleButton, signal='stateChanged', setter='setState')
register_widget(GroupBox, signal='collapseToggled', setter='collapse')
register_widget(Slider, signal='valueChanged', setter='setValue')
