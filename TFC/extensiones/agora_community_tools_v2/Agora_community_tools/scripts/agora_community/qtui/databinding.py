"""Data binding for Qt UI."""

from __future__ import division

import json
import weakref
from importlib import import_module


_REGISTERED_WIDGETS = {}


class DataBindingError(Exception):
    """Custom exception for data binding errors."""


class DataBindingAttributeError(AttributeError):
    """Custom exception for data binding attribute errors."""


# -------------------------------------------------------------------------------------------------


for qt_binding in ('Qt', 'PySide6', 'PySide2', 'PyQt6', 'PyQt5'):
    try:
        qt = import_module('{}.QtCore'.format(qt_binding))
        qtg = import_module('{}.QtGui'.format(qt_binding))
        qtw = import_module('{}.QtWidgets'.format(qt_binding))
        break
    except ImportError:
        pass
else:
    raise DataBindingError('No Qt binding found.')


# -------------------------------------------------------------------------------------------------


def bind(
    widget,
    data,
    attr_name,
    display_processor=None,
    value_processor=None,
    ignore_inner_change=False,
):
    """Bind to the widget's data value."""
    if isinstance(data, list):
        _bind_sequence(widget, data, attr_name)
    else:
        _bind_attribute(
            widget,
            data,
            attr_name,
            BindingType.VALUE,
            None,
            display_processor,
            value_processor,
            ignore_inner_change,
        )


def bind_visibility(widget, data, attr_name, display_processor=None, ignore_inner_change=False):
    """Bind to the widget's visibility."""
    _bind_attribute(
        widget,
        data,
        attr_name,
        BindingType.VISIBILITY,
        None,
        display_processor,
        ignore_inner_change=ignore_inner_change,
    )


def bind_invisibility(widget, data, attr_name, display_processor=None, ignore_inner_change=False):
    """Bind to the widget's invisibility."""
    _bind_attribute(
        widget,
        data,
        attr_name,
        BindingType.INVISIBILITY,
        None,
        display_processor,
        ignore_inner_change=ignore_inner_change,
    )


def bind_activation(widget, data, attr_name, display_processor=None, ignore_inner_change=False):
    """Bind to the widget's activation (enable/disable)."""
    _bind_attribute(
        widget,
        data,
        attr_name,
        BindingType.ACTIVATION,
        None,
        display_processor,
        ignore_inner_change=ignore_inner_change,
    )


def bind_creation(
    container,
    data,
    attr_name,
    creator,
    display_processor=None,
    ignore_inner_change=False,
):
    """Bind widget's creation."""
    if not hasattr(container, 'addWidget'):
        raise DataBindingError(
            "No 'addWidget()' method found for container of type '{}'.".format(
                container.__class__.__name__
            )
        )

    _bind_attribute(
        container,
        data,
        attr_name,
        BindingType.CREATION,
        creator,
        display_processor,
        ignore_inner_change=ignore_inner_change,
    )


def bind_callback(data, attr_name, callback, ignore_inner_change=False):
    """Bind a callback to a data attribute."""
    # TODO: Check for duplication?
    # TODO: Provide widget to listen for destruction to remove the callback?
    # TODO: Use weak method proxy internally avoiding the need for the user to do it?
    bound_attributes = data.__bound_attributes__

    binding_data = {
        'binding_type': BindingType.CALLBACK,
        'callback': callback,
        'ignore_inner_change': ignore_inner_change,
    }

    if attr_name in bound_attributes:
        bound_attributes[attr_name].append(binding_data)
    else:
        bound_attributes[attr_name] = [binding_data]


def unbind_callback(data, attr_name, callback):
    """Unbind a callback."""
    bound_attributes = data.__bound_attributes__

    if attr_name not in bound_attributes:
        return

    for index in range(len(bound_attributes[attr_name]) - 1, -1, -1):
        binding_data = bound_attributes[attr_name][index]

        if (
            binding_data['binding_type'] == BindingType.CALLBACK
            and binding_data['callback'] is callback
        ):
            del bound_attributes[attr_name][index]


def register_widget(
    cls,
    signal=None,
    signal_value_getter=None,
    signal_value_processor=None,
    setter=None,
    setter_value_processor=None,
):
    """Register widgets to make them bindable."""
    _REGISTERED_WIDGETS[cls] = {
        'signal': signal,
        'signal_value_getter': signal_value_getter,
        'signal_value_processor': signal_value_processor,
        'setter': setter,
        'setter_value_processor': setter_value_processor,
    }


# -------------------------------------------------------------------------------------------------


class BindingType(object):
    """Binding type."""

    VALUE = 1
    VISIBILITY = 2
    INVISIBILITY = 3
    ACTIVATION = 4
    CREATION = 5
    CALLBACK = 6


class BindableDataEncoder(json.JSONEncoder):
    """Helper for JSON encoding."""

    def __init__(self, obj_encoder, **kwargs):
        super(BindableDataEncoder, self).__init__(**kwargs)

        self.obj_encoder = obj_encoder

    def default(self, o):
        """Encode an object."""
        if isinstance(o, BindableData):
            return {key: value for key, value in o.__dict__.items() if not key.startswith('_')}

        if self.obj_encoder:
            try:
                return self.obj_encoder(o)
            except TypeError:
                pass

        return super(BindableDataEncoder, self).default(o)


class BindableData(object):
    """An object that can be used for UI data binding."""

    # TODO: Create bindable dict!
    __BIND_DICT__ = True

    __slots__ = ['__dict__', '__weakref__', '__bound_attributes__', '__bound_root__']

    def __init__(self, **attributes):
        self.__bound_attributes__ = {}
        self.__bound_root__ = ()

        default_attributes = self.default_attributes

        for name, value in default_attributes.items():
            self.__dict__[name] = _sanitize_attribute_value(
                value,
                self.__BIND_DICT__,
                from_init=True,
            )

            if isinstance(self.__dict__[name], (BindableData, BindableList)):
                self.__dict__[name].__bound_root__ = (weakref.ref(self), name)

        for name, value in attributes.items():
            # if name not in self.__dict__ and self.__class__ is not BindableData:
            #     raise DataBindingAttributeError(
            #         "'{}' object has no attribute '{}'".format(self.__class__.__name__, name)
            #     )

            self.__dict__[name] = _sanitize_attribute_value(value, self.__BIND_DICT__)

            if isinstance(self.__dict__[name], (BindableData, BindableList)):
                self.__dict__[name].__bound_root__ = (weakref.ref(self), name)

    @property
    def attributes(self):
        """Retrieve the data attributes."""
        attributes = {}

        for name, value in self.__dict__.items():
            if not name.startswith('_'):
                attributes[name] = value

        return attributes

    @property
    def default_attributes(self):
        """Retrieve the default attributes."""
        return _find_class_default_attributes(self.__class__)

    def __setattr__(self, name, value):
        if name.startswith('_') or isinstance(getattr(type(self), name, None), property):
            super(BindableData, self).__setattr__(name, value)
            return

        try:
            attr_value = self.__dict__[name]
        except KeyError:
            if self.__class__ is not BindableData:
                raise DataBindingAttributeError(
                    "'{}' object has no attribute '{}'".format(self.__class__.__name__, name)
                )

            attr_value = None

        if isinstance(attr_value, BindableData) and value is not None:
            # TOOD: Check only public attributes (`set(attr_value) != set(value)` is wrong).
            if attr_value.__class__ is not BindableData and set(attr_value) != set(value):
                raise DataBindingAttributeError(
                    "The value for '{}.{}' have unknown/missing attributes.".format(
                        self.__class__.__name__, name
                    )
                )

            # temporarily stop root changes propagation
            bound_root, attr_value.__bound_root__ = attr_value.__bound_root__, ()

            try:
                for attr_name in value:
                    attr_value[attr_name] = value[attr_name]

                for attr_name in list(attr_value):
                    if attr_name not in value:
                        del attr_value[attr_name]
            finally:
                attr_value.__bound_root__ = bound_root

            _sync_bound_attributes(self, name)

            # TODO: Test for call after `_sync_bound_attributes` to have the UI updated on callback.
            _on_attribute_changed(self, name, attr_value)
        elif isinstance(attr_value, BindableList):
            attr_value[:] = value
        else:
            sanitized_value = _sanitize_attribute_value(value)

            super(BindableData, self).__setattr__(name, sanitized_value)

            if isinstance(sanitized_value, (BindableData, BindableList)):
                sanitized_value.__bound_root__ = (weakref.ref(self), name)

            _sync_bound_attributes(self, name)

            # TODO: Test for call after `_sync_bound_attributes` to have the UI updated on callback.
            _on_attribute_changed(self, name, sanitized_value)
            _notify_root_about_changes(self)

    def __getitem__(self, name):
        return getattr(self, name)

    def __setitem__(self, name, value):
        self.__setattr__(name, value)

    def __delitem__(self, name):
        self.__delattr__(name)

    def __iter__(self):
        return self.__dict__.__iter__()

    def __repr__(self):
        attributes = ', '.join(self)

        return '{}({})'.format(self.__class__.__name__, attributes)

    def __str__(self):
        return str(self.__dict__)

    def __bool__(self):
        return bool(self.__dict__)

    def __nonzero__(self):
        return bool(self.__dict__)

    def __eq__(self, obj):
        return self.__dict__ == obj

    def clear(self):
        """Clear all data."""
        self.__dict__.clear()

    def json_dump(self, beautify=False, obj_encoder=None):
        """Encode to JSON."""
        return json.dumps(
            self,
            cls=BindableDataEncoder,
            obj_encoder=obj_encoder,
            sort_keys=False,
            indent=4 if beautify else None,
            separators=(',', ': ') if beautify else (',', ':'),
        )

    def on_attribute_changed(self, name, value):
        """Call when an attribute is changed."""


class BindableList(list):
    """A list that can be used for data binding."""

    def __init__(self, *args, **kwargs):
        super(BindableList, self).__init__(*args, **kwargs)

        self.__bound_sequence__ = []
        self.__bound_root__ = ()

        for i, value in enumerate(self):
            super(BindableList, self).__setitem__(i, _sanitize_attribute_value(value))

    def __iadd__(self, iterable):
        previous_length = len(self)

        super(BindableList, self).__iadd__(iterable)

        for i in range(previous_length, len(self)):
            super(BindableList, self).__setitem__(i, _sanitize_attribute_value(self[i]))

        _sync_bound_sequence(self)

        return self

    def __imul__(self, scalar):
        super(BindableList, self).__imul__(scalar)

        _sync_bound_sequence(self)

        return self

    def __setitem__(self, index, item):
        if isinstance(index, slice):
            super(BindableList, self).__setitem__(index, item)

            for i, value in enumerate(self):
                super(BindableList, self).__setitem__(i, _sanitize_attribute_value(value))

            _sync_bound_sequence(self)
        else:
            item = _sanitize_attribute_value(item)

            super(BindableList, self).__setitem__(index, item)

            _sync_bound_sequence_update(self, index, item)

    def __setslice__(self, start, stop, sequence):
        super(BindableList, self).__setslice__(start, stop, sequence)

        for i, value in enumerate(self):
            super(BindableList, self).__setitem__(i, _sanitize_attribute_value(value))

        _sync_bound_sequence(self)

    def __delitem__(self, index):
        super(BindableList, self).__delitem__(index)

        if isinstance(index, slice):
            _sync_bound_sequence(self)
        else:
            _sync_bound_sequence_removal(self, index)

    def __delslice__(self, start, stop):
        super(BindableList, self).__delslice__(start, stop)

        _sync_bound_sequence(self)

    def append(self, item):
        """Add an item to the end of the list."""
        item = _sanitize_attribute_value(item)

        super(BindableList, self).append(item)

        _sync_bound_sequence_insertion(self, len(self) - 1, item)

    def extend(self, iterable):
        """Extend the list by appending all the items from the iterable."""
        previous_length = len(self)

        super(BindableList, self).extend(iterable)

        for i in range(previous_length, len(self)):
            super(BindableList, self).__setitem__(i, _sanitize_attribute_value(self[i]))

        _sync_bound_sequence(self)

    def insert(self, index, item):
        """Insert an item at a given position."""
        item = _sanitize_attribute_value(item)

        super(BindableList, self).insert(index, item)

        if index >= len(self):
            # append behaviour if index is out of range
            index = len(self) - 1

        _sync_bound_sequence_insertion(self, index, item)

    def pop(self, index):
        """Remove the item at the given position in the list, and return it."""
        item = super(BindableList, self).pop(index)

        _sync_bound_sequence_removal(self, index)

        return item

    def remove(self, item):
        """Remove the first found item from the list."""
        index = self.index(item)

        super(BindableList, self).remove(item)

        _sync_bound_sequence_removal(self, index)

    def reverse(self):
        """Reverse the elements of the list in place."""
        super(BindableList, self).reverse()

        _sync_bound_sequence(self)

    def sort(self, *args, **kwargs):
        """Sort the items of the list in place."""
        super(BindableList, self).sort(*args, **kwargs)

        _sync_bound_sequence(self)


class BindableIndex(object):
    """A custom integer that can be used as a mutable/bindable index."""

    __slots__ = ['__bound_attributes__', 'value']

    def __init__(self, value=0):
        self.__bound_attributes__ = {}
        self.value = int(value)

    def __setattr__(self, name, value):
        super(BindableIndex, self).__setattr__(name, value)

        _sync_bound_attributes(self, name)

    def __hash__(self):
        return hash(self.value)

    def __int__(self):
        return self.value

    def __index__(self):
        return self.value

    def __float__(self):
        return float(self.value)

    def __bool__(self):
        return bool(self.value)

    def __nonzero__(self):
        return bool(self.value)

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return 'BindableIndex({})'.format(self.value)

    def __eq__(self, other):
        return self.value == other

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        return self.value < other

    def __le__(self, other):
        return self.value <= other

    def __gt__(self, other):
        return self.value > other

    def __ge__(self, other):
        return self.value >= other

    def __add__(self, other):
        if isinstance(other, BindableIndex):
            return self.value + other.value

        return self.value + other

    def __radd__(self, other):
        return other + self.value

    def __iadd__(self, other):
        if isinstance(other, BindableIndex):
            self.value = int(self.value + other.value)
        else:
            self.value = int(self.value + other)

        return self

    def __sub__(self, other):
        if isinstance(other, BindableIndex):
            return self.value - other.value

        return self.value - other

    def __rsub__(self, other):
        return other - self.value

    def __isub__(self, other):
        if isinstance(other, BindableIndex):
            self.value = int(self.value - other.value)
        else:
            self.value = int(self.value - other)

        return self

    def __mul__(self, other):
        if isinstance(other, BindableIndex):
            return self.value * other.value

        return self.value * other

    def __rmul__(self, other):
        return other * self.value

    def __imul__(self, other):
        if isinstance(other, BindableIndex):
            self.value = int(self.value * other.value)
        else:
            self.value = int(self.value * other)

        return self

    def __div__(self, other):
        return self.__truediv__(other)

    def __rdiv__(self, other):
        return self.__rtruediv__(other)

    def __idiv__(self, other):
        return self.__itruediv__(other)

    def __truediv__(self, other):
        if isinstance(other, BindableIndex):
            return self.value / other.value

        return self.value / other

    def __rtruediv__(self, other):
        return other / self.value

    def __itruediv__(self, other):
        if isinstance(other, BindableIndex):
            self.value = int(self.value / other.value)
        else:
            self.value = int(self.value / other)

        return self

    def __floordiv__(self, other):
        if isinstance(other, BindableIndex):
            return self.value // other.value

        return self.value // other

    def __rfloordiv__(self, other):
        return other // self.value

    def __ifloordiv__(self, other):
        if isinstance(other, BindableIndex):
            self.value = int(self.value // other.value)
        else:
            self.value = int(self.value // other)

        return self

    def __mod__(self, other):
        if isinstance(other, BindableIndex):
            return self.value % other.value

        return self.value % other

    def __rmod__(self, other):
        return other % self.value


# -------------------------------------------------------------------------------------------------


def _bind_attribute(
    widget,
    data,
    attr_name,
    binding_type,
    callback=None,
    display_processor=None,
    value_processor=None,
    ignore_inner_change=False,
):
    widget_ref = weakref.ref(widget)
    bound_attributes = data.__bound_attributes__

    if binding_type == BindingType.CREATION:
        binding_data = {
            'widget_ref': None,
            'container_view_ref': widget_ref,
            'view_creator': callback,
            'binding_type': binding_type,
            'display_processor': display_processor,
            'ignore_inner_change': ignore_inner_change,
        }
    else:
        binding_data = {
            'widget_ref': widget_ref,
            'binding_type': binding_type,
            'display_processor': display_processor,
            'value_processor': value_processor,
            'ignore_inner_change': ignore_inner_change,
        }

    if attr_name in bound_attributes:
        bound_attributes[attr_name].append(binding_data)
    else:
        bound_attributes[attr_name] = [binding_data]

    widget.destroyed.connect(
        lambda: bound_attributes[attr_name].remove(binding_data)
        if binding_data in bound_attributes[attr_name]
        else None
    )

    attr_value = getattr(data, attr_name)
    processed_value = display_processor(attr_value) if display_processor else attr_value

    if binding_type == BindingType.VISIBILITY:
        widget.setVisible(bool(processed_value))
    elif binding_type == BindingType.INVISIBILITY:
        widget.setHidden(bool(processed_value))
    elif binding_type == BindingType.ACTIVATION:
        widget.setEnabled(bool(processed_value))
    elif binding_type == BindingType.CREATION:
        _sync_bound_attributes(data, attr_name, binding_data=binding_data)
    else:
        widget_data = _get_registered_widget_data(widget)

        if widget_data:
            if widget_data['signal']:
                getattr(widget, widget_data['signal']).connect(
                    lambda *value: _on_widget_value_changed(
                        widget_ref,
                        data,
                        attr_name,
                        value,
                        value_processor,
                        binding_type,
                    )
                )

        _update_widget_value(widget, attr_value, display_processor)


def _bind_sequence(container_widget, data, item_view_creator):
    binding_data = {
        'container_view_ref': weakref.ref(container_widget),
        'item_view_creator': item_view_creator,
        'items_views': [],
    }

    data.__bound_sequence__.append(binding_data)

    container_widget.destroyed.connect(
        lambda: data.__bound_sequence__.remove(binding_data)
        if binding_data in data.__bound_sequence__
        else None
    )

    _sync_bound_sequence(data, len(data.__bound_sequence__) - 1)


def _sync_bound_attributes(
    data,
    attr_name,
    widget_instigator=None,
    binding_data=None,
    root_sync=False,
):
    attr_value = getattr(data, attr_name)

    if binding_data:
        bound_widgets = [binding_data]
    else:
        try:
            bound_widgets = data.__bound_attributes__[attr_name]
        except KeyError:
            # No widgets bound to the attribute.
            return

    for bound_data in bound_widgets:
        binding_type = bound_data['binding_type']

        if binding_type == BindingType.CALLBACK:
            continue

        if root_sync and bound_data['ignore_inner_change']:
            continue

        widget = bound_data['widget_ref']() if bound_data['widget_ref'] else None

        if (
            widget_instigator
            and widget_instigator[0] is widget
            and widget_instigator[1] == binding_type
        ):
            continue

        processed_value = attr_value

        if bound_data['display_processor']:
            processed_value = bound_data['display_processor'](attr_value)

        if binding_type == BindingType.VISIBILITY:
            widget.setVisible(bool(processed_value))
        elif binding_type == BindingType.INVISIBILITY:
            widget.setHidden(bool(processed_value))
        elif binding_type == BindingType.ACTIVATION:
            widget.setEnabled(bool(processed_value))
        elif binding_type == BindingType.CREATION:
            if widget:
                for child in widget.findChildren(qtw.QWidget):
                    for attr in data.__bound_attributes__:
                        for i, child_data in enumerate(data.__bound_attributes__[attr]):
                            if (
                                'widget_ref' in child_data  # not present for BindingType.CALLBACK
                                and child_data['widget_ref']
                                and child_data['widget_ref']() is child
                            ):
                                del data.__bound_attributes__[attr][i]

                widget.hide()
                widget.deleteLater()
                bound_data['widget_ref'] = None

            if processed_value:
                widget = bound_data['view_creator']()
                bound_data['container_view_ref']().addWidget(widget)
                bound_data['widget_ref'] = weakref.ref(widget)
        else:
            _update_widget_value(widget, attr_value, bound_data['display_processor'])


def _sync_bound_sequence(data, widget_index=None):
    if widget_index:
        bound_sequence_data = [data.__bound_sequence__[widget_index]]
    else:
        bound_sequence_data = data.__bound_sequence__

    for bound_data in bound_sequence_data:
        container_view = bound_data['container_view_ref']()
        items_views = bound_data['items_views']

        if isinstance(container_view, qtw.QListWidget):
            container_view.clear()
        elif isinstance(container_view, qtw.QComboBox):
            selected_combobox_text = container_view.currentText()
            container_view.clear()
        else:
            for item in items_views:
                item['view'].deleteLater()

            if isinstance(container_view, qtw.QTabWidget):
                container_view.clear()

        del items_views[:]

    for index, item in enumerate(data):
        for bound_data in bound_sequence_data:
            container_view = bound_data['container_view_ref']()
            bound_index = BindableIndex(index)

            if bound_data['item_view_creator']:
                item_view = bound_data['item_view_creator'](item, bound_index, data)
            else:
                item_view = item

            if isinstance(container_view, qtw.QComboBox):
                container_view.addItem(str(item_view))

                if selected_combobox_text == str(item_view):
                    container_view.setCurrentText(selected_combobox_text)
            elif isinstance(container_view, qtw.QListWidget):
                if isinstance(item_view, qtw.QWidget):
                    item = qtw.QListWidgetItem()
                    item.setSizeHint(item_view.minimumSizeHint())

                    container_view.addItem(item)
                    container_view.setItemWidget(item, item_view)
                else:
                    container_view.addItem(str(item_view))
            elif isinstance(container_view, qtw.QTabWidget):
                if isinstance(item_view, tuple):
                    item_view, tab_label = item_view
                else:
                    tab_label = ''

                container_view.addTab(item_view, tab_label)
            else:
                container_view.addWidget(item_view)

            bound_data['items_views'].append({'index': bound_index, 'view': item_view})

    # TODO: Test for call after the UI is updated in case the callback needs the changes.
    _notify_root_about_changes(data)


def _sync_bound_sequence_update(data, index, item):
    for bound_data in data.__bound_sequence__:
        container_view = bound_data['container_view_ref']()
        bound_view = bound_data['items_views'][index]
        bound_index = bound_view['index']

        if bound_data['item_view_creator']:
            item_view = bound_data['item_view_creator'](item, bound_index, data)
        else:
            item_view = item

        if isinstance(container_view, qtw.QComboBox):
            container_view.setItemText(index, str(item_view))
        elif isinstance(container_view, qtw.QListWidget):
            if isinstance(bound_view['view'], qtw.QWidget):
                bound_view['view'].deleteLater()

                item = container_view.item(index)
                item.setSizeHint(item_view.minimumSizeHint())

                container_view.setItemWidget(item, item_view)
            else:
                container_view.item(index).setText(str(item_view))
        elif isinstance(container_view, qtw.QTabWidget):
            bound_view['view'].deleteLater()
            container_view.removeTab(container_view.indexOf(bound_view['view']))

            if isinstance(item_view, tuple):
                item_view, tab_label = item_view
            else:
                tab_label = ''

            container_view.insertTab(index, item_view, tab_label)
        else:
            bound_view['view'].deleteLater()

            container_view.insertWidget(index, item_view)

        bound_view['view'] = item_view

    # TODO: Test for call after the UI is updated in case the callback needs the changes.
    _notify_root_about_changes(data)


def _sync_bound_sequence_insertion(data, index, item):
    for bound_data in data.__bound_sequence__:
        container_view = bound_data['container_view_ref']()
        items_views = bound_data['items_views']

        bound_index = BindableIndex(index)

        if bound_data['item_view_creator']:
            item_view = bound_data['item_view_creator'](item, bound_index, data)
        else:
            item_view = item

        if isinstance(container_view, qtw.QComboBox):
            container_view.insertItem(index, str(item_view))
        elif isinstance(container_view, qtw.QListWidget):
            if isinstance(item_view, qtw.QWidget):
                item = qtw.QListWidgetItem()
                item.setSizeHint(item_view.minimumSizeHint())

                container_view.insertItem(index, item)
                container_view.setItemWidget(item, item_view)
            else:
                container_view.insertItem(index, str(item_view))
        elif isinstance(container_view, qtw.QTabWidget):
            if isinstance(item_view, tuple):
                item_view, tab_label = item_view
            else:
                tab_label = ''

            container_view.insertTab(index, item_view, tab_label)
        else:
            container_view.insertWidget(index, item_view)

        items_views.insert(index, {'index': bound_index, 'view': item_view})

        for i in range(index, len(items_views)):
            items_views[i]['index'].value = i

    # TODO: Test for call after the UI is updated in case the callback needs the changes.
    _notify_root_about_changes(data)


def _sync_bound_sequence_removal(data, index):
    for bound_data in data.__bound_sequence__:
        container_view = bound_data['container_view_ref']()
        items_views = bound_data['items_views']

        if isinstance(container_view, qtw.QComboBox):
            container_view.removeItem(index)
        elif isinstance(container_view, qtw.QListWidget):
            current_row = container_view.currentRow()
            rows_count = container_view.count()

            if current_row == index:
                new_index = index - 1 if index == rows_count - 1 else index
            else:
                new_index = current_row - 1 if index < current_row else current_row

            container_view.setCurrentRow(-1)
            container_view.takeItem(index)
            container_view.setCurrentRow(new_index)
        elif isinstance(container_view, qtw.QTabWidget):
            items_views[index]['view'].deleteLater()
            container_view.removeTab(index)
        else:
            items_views[index]['view'].deleteLater()

            if hasattr(container_view, 'removeWidget'):
                # TODO: Test with pop and insert right away.
                # Force `removeWidget` to be present in container.
                container_view.removeWidget(items_views[index]['view'])

        del items_views[index]

        for i in range(index, len(items_views)):
            items_views[i]['index'].value = i

    # TODO: Test for call after the UI is updated in case the callback needs the changes.
    _notify_root_about_changes(data)


# -------------------------------------------------------------------------------------------------


def _is_custom_class_instance(obj):
    return type(obj).__module__ != object.__module__


def _find_class_default_attributes(cls):
    """Find the default attributes for a derived class."""
    attributes = {}

    for base_class in reversed(cls.__mro__[:-1]):
        for name, value in base_class.__dict__.items():
            is_valid_attribute = (
                not name.startswith('_')
                and not name.isupper()
                and not callable(value)
                and not isinstance(value, property)
                and not isinstance(value, classmethod)
                and not isinstance(value, staticmethod)
            )

            if is_valid_attribute:
                attributes[name] = value

    return attributes


def _sanitize_attribute_value(value, bind_dict=True, from_init=False):
    if isinstance(value, list) and not isinstance(value, BindableList):
        return BindableList(value)

    # TODO: Create BindableDict.
    if isinstance(value, dict) and bind_dict:
        return BindableData(**value)

    if from_init:
        if isinstance(value, BindableData):
            return value.__class__(**value.attributes)

        if isinstance(value, dict) and not bind_dict:
            return dict(**value)

        # TODO: This is problematic! Test with an empty class inherited from `str`.
        # if _is_custom_class_instance(value):
        #     return BindableData(**_find_class_default_attributes(value.__class__))

    return value


def _notify_root_about_changes(data):
    if not data.__bound_root__:
        return

    root = data.__bound_root__[0]()
    attr_name = data.__bound_root__[1]

    if root:
        _sync_bound_attributes(root, attr_name, root_sync=True)

        # TODO: Test for call after `_sync_bound_attributes` to have the UI updated on callback.
        _on_attribute_changed(root, attr_name, data, root_sync=True)


def _update_widget_value(widget, value, display_processor):
    if display_processor:
        value = display_processor(value)

    widget.__databinding_update_in_progress__ = True

    widget_data = _get_registered_widget_data(widget)

    if widget_data:
        if widget_data['setter']:
            if callable(widget_data['setter']):
                widget_data['setter'](widget, value)
            else:
                if widget_data['setter_value_processor']:
                    # TODO: Do this for setter callback too.
                    value = widget_data['setter_value_processor'](value)

                getattr(widget, widget_data['setter'])(value)
    else:
        del widget.__databinding_update_in_progress__

        raise DataBindingError(
            "No value update implementation for widget '{}'".format(widget.__class__.__name__)
        )

    del widget.__databinding_update_in_progress__


def _on_widget_value_changed(widget_ref, data, attr_name, value, value_processor, binding_type):
    widget = widget_ref()

    if hasattr(widget, '__databinding_update_in_progress__'):
        return

    widget_data = _get_registered_widget_data(widget)

    if widget_data['signal_value_getter']:
        if callable(widget_data['signal_value_getter']):
            value = widget_data['signal_value_getter'](widget)
        else:
            value = getattr(widget, widget_data['signal_value_getter'])()
    else:
        value = value[0]

    if widget_data['signal_value_processor']:
        try:
            value = widget_data['signal_value_processor'](widget, value)
        except ValueError:
            return

    if isinstance(widget, qtw.QCheckBox):
        # preserve attribute type if it is int and not bool
        value = type(data.__dict__[attr_name])(value)
    elif isinstance(widget, qtw.QComboBox):
        item_data = widget.itemData(value)

        if item_data is not None:
            value = item_data
        else:
            value = widget.itemText(value)

    if value_processor:
        value = value_processor(value)

    data.__dict__[attr_name] = value

    _sync_bound_attributes(data, attr_name, (widget, binding_type))

    # TODO: Test for call after `_sync_bound_attributes` to have the UI updated on callback.
    _on_attribute_changed(data, attr_name, value)

    # TODO: Add tests for this.
    _notify_root_about_changes(data)


def _on_attribute_changed(data, attr_name, value, root_sync=False):
    data.on_attribute_changed(attr_name, value)

    try:
        bound_callbacks = data.__bound_attributes__[attr_name]
    except KeyError:
        # No callbacks bound to the attribute.
        return

    for bound_data in bound_callbacks:
        if bound_data['binding_type'] != BindingType.CALLBACK:
            continue

        if root_sync and bound_data['ignore_inner_change']:
            continue

        bound_data['callback'](value)


# -------------------------------------------------------------------------------------------------


def _widget_signal_value_processor_lineedit(widget, value):
    # TODO: Add `hasAcceptableInput()` logic.
    if isinstance(widget.validator(), qtg.QIntValidator):
        value = int(value)
    elif isinstance(widget.validator(), qtg.QDoubleValidator):
        value = float(value)

    return value


def _widget_setter_combobox(widget, value):
    item_index = widget.findData(value)
    value_text = str(value)

    if item_index != -1:
        widget.setCurrentIndex(item_index)
    elif value_text:
        found_index = widget.findText(value_text)

        if found_index == -1:
            raise DataBindingError('Value "{}" was not found in QComboBox.'.format(value_text))

        if widget.itemData(found_index) is not None:
            raise DataBindingError('Value "{}" was not found in QComboBox.'.format(value_text))

        widget.setCurrentText(value_text)
    else:
        widget.setCurrentIndex(-1)


def _widget_setter_listwidget(widget, value):
    try:
        single_selection_mode = qtw.QAbstractItemView.SelectionMode.SingleSelection
    except AttributeError:
        single_selection_mode = qtw.QAbstractItemView.SingleSelection

    if widget.selectionMode() == single_selection_mode:
        widget.setCurrentRow(value)
    else:
        widget.clearSelection()

        for row in value:
            widget.item(row).setSelected(True)


def _widget_signal_value_getter_listwidget(widget):
    try:
        single_selection_mode = qtw.QAbstractItemView.SelectionMode.SingleSelection
    except AttributeError:
        single_selection_mode = qtw.QAbstractItemView.SingleSelection

    selected_items = widget.selectedItems()

    if widget.selectionMode() == single_selection_mode:
        if selected_items:
            return widget.row(selected_items[0])

        return -1

    return [widget.row(item) for item in selected_items]


def _get_registered_widget_data(widget):
    if widget.__class__ in _REGISTERED_WIDGETS:
        return _REGISTERED_WIDGETS[widget.__class__]

    for cls, data in _REGISTERED_WIDGETS.items():
        if isinstance(widget, cls):
            return data

    return None


# -------------------------------------------------------------------------------------------------


register_widget(
    qtw.QLineEdit,
    signal='textChanged',
    signal_value_processor=_widget_signal_value_processor_lineedit,
    setter='setText',
    setter_value_processor=str,
)

register_widget(
    qtw.QCheckBox,
    signal='stateChanged',
    signal_value_processor=lambda _widget, value: bool(value),
    setter='setChecked',
)

register_widget(
    qtw.QLabel,
    setter='setText',
    setter_value_processor=str,
)

register_widget(
    qtw.QPushButton,
    setter='setText',
    setter_value_processor=str,
)

register_widget(
    qtw.QComboBox,
    signal='currentIndexChanged',
    setter=_widget_setter_combobox,
)

register_widget(
    qtw.QListWidget,
    signal='itemSelectionChanged',
    signal_value_getter=_widget_signal_value_getter_listwidget,
    setter=_widget_setter_listwidget,
)

register_widget(
    qtw.QTabWidget,
    signal='currentChanged',
    setter='setCurrentIndex',
)

register_widget(
    qtw.QTextEdit,
    signal='textChanged',
    signal_value_getter='toPlainText',
    setter='setPlainText',
    setter_value_processor=str,
)
