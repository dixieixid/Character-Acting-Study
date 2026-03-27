"""The UI for the attribute swapping."""

from functools import partial

from agora_community.vendor import mayax as mx
from agora_community import qtui

from .. import core
from . import main


def create_attr_swapper_panel(state):
    # type: (main.MainState) -> qtui.QWidget
    """Create the UI for the attribute swapping."""
    with qtui.GroupVBox('Attribute Swapper', collapsed=True) as main_box:
        main_box.setToolTip('Swap attribute values while preserving the motion.')
        main_box.layout().setContentsMargins(
            4 * qtui.SCALE_FACTOR,
            4 * qtui.SCALE_FACTOR,
            4 * qtui.SCALE_FACTOR,
            4 * qtui.SCALE_FACTOR,
        )
        main_box.layout().setSpacing(2 * qtui.SCALE_FACTOR)

        qtui.addStyleClass(main_box, 'section')

        with qtui.QPushButton('Swap Attribute') as btn:
            btn.setToolTip('Swap the value of the selected attribute while preserving the motion.')
            btn.clicked.connect(partial(_on_swap_attr, state, btn))

            qtui.bind_activation(
                btn,
                state,
                'selected_attributes',
                display_processor=lambda _value: _should_enable_swap_attr_button(state),
            )
            qtui.bind_activation(
                btn,
                state,
                'operation_in_progress',
                display_processor=lambda _value: _should_enable_swap_attr_button(state),
            )

        with qtui.QPushButton('Swap Rotate Order') as btn:
            btn.setToolTip('Change the rotation order while preserving the motion.')
            btn.clicked.connect(partial(_on_swap_rotate_order, state, btn))

            qtui.bind_activation(
                btn,
                state,
                'selected_objects_count',
                display_processor=lambda _value: _should_enable_swap_rotate_order_button(state),
            )
            qtui.bind_activation(
                btn,
                state,
                'operation_in_progress',
                display_processor=lambda _value: _should_enable_swap_rotate_order_button(state),
            )

    return main_box


@main.error_dialog
def _on_swap_attr(state, swap_button):
    selected_objects = mx.cmd.ls(selection=True, transforms=True)

    if not selected_objects:
        return

    attr_name = state.selected_attributes[0]

    qtui.PopupPanel.open(
        swap_button,
        partial(_create_swap_attr_ui, state, selected_objects, attr_name),
    )


@main.error_dialog
def _on_swap_rotate_order(state, swap_button):
    selected_objects = mx.cmd.ls(selection=True, transforms=True)

    if not selected_objects:
        return

    qtui.PopupPanel.open(
        swap_button,
        partial(_create_swap_rotate_order_ui, state, selected_objects),
    )


@main.error_dialog
def _create_swap_attr_ui(state, selected_objects, attr_name, popup):
    def _on_apply():
        popup.close()

        main.swap_attribute(state, selected_objects, attr_name, attr_field_getter())

    last_object = selected_objects[-1]

    attr_name = mx.cmd.attributeQuery(attr_name, node=last_object, longName=True)
    attr_nice_name = mx.cmd.attributeQuery(attr_name, node=last_object, niceName=True)
    attr_type = last_object[attr_name].type
    attr_value = last_object[attr_name].value

    if isinstance(attr_value, float):
        attr_value = round(attr_value, 3)

    if attr_type == 'enum':
        all_enum_values = []
        last_object_enum_value = core.get_enum_values(last_object, attr_name)[attr_value]

        for obj in selected_objects:
            try:
                obj_attr = obj[attr_name]
            except mx.MayaAttributeError:
                continue

            if obj_attr.type == 'enum':
                for enum_value in core.get_enum_values(obj, attr_name):
                    if enum_value not in all_enum_values:
                        all_enum_values.append(enum_value)

        attr_field = qtui.QComboBox()
        attr_field_getter = attr_field.currentText

        for enum_label in all_enum_values:
            attr_field.addItem(enum_label)

            if enum_label == last_object_enum_value:
                attr_field.setCurrentText(enum_label)
    elif attr_type in ('double', 'doubleLinear', 'doubleAngle', 'long'):
        is_range = mx.cmd.attributeQuery(attr_name, node=last_object, rangeExists=True)

        if is_range:
            min_value = mx.cmd.attributeQuery(attr_name, node=last_object, minimum=True)[0]
            max_value = mx.cmd.attributeQuery(attr_name, node=last_object, maximum=True)[0]

            if attr_type == 'long':
                min_value = int(min_value)
                max_value = int(max_value)

            attr_field = qtui.Slider(min_value, max_value)
            attr_field.setValue(attr_value)

            attr_field_getter = attr_field.value
        else:
            if attr_type == 'long':
                field_validator = qtui.QIntValidator()
            else:
                field_validator = qtui.QDoubleValidator()
                field_validator.setNotation(qtui.QDoubleValidator.StandardNotation)
                field_validator.setLocale(qtui.QLocale(qtui.QLocale.English))

            attr_field = qtui.QLineEdit(str(attr_value))
            attr_field.setValidator(field_validator)

            attr_field_getter = lambda: float(attr_field.text())

        attr_field.returnPressed.connect(_on_apply)
    elif attr_type == 'bool':
        attr_field = qtui.QCheckBox()
        attr_field.setChecked(attr_value)

        attr_field_getter = attr_field.isChecked
    else:
        attr_field = qtui.QLabel('<{}> type not supported.'.format(attr_type))

    with qtui.QWidget() as widget:
        with qtui.QVBoxLayout() as main_layout:
            widget.setLayout(main_layout)

            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)

            main_layout.addWidget(_create_selected_objects_title_ui())

            with qtui.QHBoxLayout() as layout:
                layout.setSpacing(4 * qtui.SCALE_FACTOR)

                layout.setContentsMargins(
                    4 * qtui.SCALE_FACTOR,
                    4 * qtui.SCALE_FACTOR,
                    4 * qtui.SCALE_FACTOR,
                    4 * qtui.SCALE_FACTOR,
                )

                with qtui.QLabel(attr_nice_name):
                    pass

                layout.addWidget(attr_field)

                with qtui.QPushButton('Swap') as btn:
                    btn.clicked.connect(_on_apply)

                    qtui.addStyleClass(btn, 'apply-button')

    return widget


@main.error_dialog
def _create_swap_rotate_order_ui(state, selected_objects, popup):
    gimbal_info = core.gimbal_info(selected_objects)
    selected_objects_count = len(selected_objects)

    def _on_apply(rotate_order):
        popup.close()

        main.swap_rotate_order(state, selected_objects, rotate_order)

    with qtui.QWidget() as main_widget:
        qtui.addStyleClass(main_widget, 'rotate-order-swapper')

        with qtui.QVBoxLayout() as main_layout:
            main_widget.setLayout(main_layout)

            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)

            main_layout.addWidget(_create_selected_objects_title_ui())

            for rotate_order_info in gimbal_info:
                with qtui.QWidget() as row_widget:
                    qtui.addStyleClass(row_widget, 'rotate-order-swapper__row')

                    if rotate_order_info['order'] % 2:
                        qtui.addStyleClass(row_widget, 'rotate-order-swapper__row--even')
                    else:
                        qtui.addStyleClass(row_widget, 'rotate-order-swapper__row--odd')

                    with qtui.QHBoxLayout() as row_layout:
                        row_widget.setLayout(row_layout)

                        row_layout.setContentsMargins(
                            4 * qtui.SCALE_FACTOR,
                            4 * qtui.SCALE_FACTOR,
                            6 * qtui.SCALE_FACTOR,
                            4 * qtui.SCALE_FACTOR,
                        )
                        row_layout.setSpacing(6 * qtui.SCALE_FACTOR)

                        with qtui.QPushButton(rotate_order_info['label']) as btn:
                            btn.clicked.connect(partial(_on_apply, rotate_order_info['order']))
                            btn.setDisabled(rotate_order_info['shared'])
                            btn.setSizePolicy(qtui.QSizePolicy.Minimum, qtui.QSizePolicy.Minimum)

                            qtui.addStyleClass(btn, 'apply-button')

                        with qtui.QVBoxLayout() as row_text_layout:
                            row_text_layout.setSpacing(0)
                            row_layout.setStretchFactor(row_text_layout, 1)

                            with qtui.QLabel() as label:
                                label_text = ', '.join(
                                    '<b>{}%</b>'.format(tolerance)
                                    for tolerance in rotate_order_info['gimbal_tolerances'][:4]
                                )

                                if len(rotate_order_info['gimbal_tolerances']) > 4:
                                    label_text += ', ...'

                                label_text += ' gimballed'

                                label.setText(label_text)

                            with qtui.QLabel() as label:
                                label_text = ''
                                label_classes = []

                                if rotate_order_info['recommended_count']:
                                    if selected_objects_count > 1:
                                        label_text = '{}/{} recommended'.format(
                                            rotate_order_info['recommended_count'],
                                            selected_objects_count,
                                        )
                                    else:
                                        label_text = 'recommended'

                                    label_classes.append('recommended')
                                elif rotate_order_info['recommended_world_count']:
                                    if selected_objects_count > 1:
                                        label_text = '{}/{} recommended for worldspace'.format(
                                            rotate_order_info['recommended_world_count'],
                                            selected_objects_count,
                                        )
                                    else:
                                        label_text = 'recommended for worldspace'

                                    label_classes.extend(['recommended', 'recommended--world'])
                                elif rotate_order_info['recommended_nonworld_count']:
                                    if selected_objects_count > 1:
                                        label_text = '{}/{} non-worldspace recommendation'.format(
                                            rotate_order_info['recommended_nonworld_count'],
                                            selected_objects_count,
                                        )
                                    else:
                                        label_text = 'non-worldspace recommendation'

                                    label_classes.extend(['recommended', 'recommended--world'])
                                else:
                                    label.setFixedHeight(0)

                                label.setText('<b>{}</b>'.format(label_text))

                                for cls in label_classes:
                                    qtui.addStyleClass(label, 'rotate-order-swapper__' + cls)

    return main_widget


def _create_selected_objects_title_ui():
    title = ''
    selected_objects = mx.cmd.ls(selection=True, transforms=True)

    if not selected_objects:
        title = ''
    elif len(selected_objects) == 1:
        title = selected_objects[0].name
    else:
        title = '{}, ... + {} more'.format(selected_objects[-1].name, len(selected_objects) - 1)

    label = qtui.QLabel(title)
    label.setAlignment(qtui.Qt.AlignCenter)

    qtui.addStyleClass(label, 'attr-swapper__title')

    return label


def _should_enable_swap_attr_button(state):
    # type: (main.MainState) -> bool
    return not state.operation_in_progress and core.is_attribute_swapping_available()


def _should_enable_swap_rotate_order_button(state):
    # type: (main.MainState) -> bool
    return not state.operation_in_progress and core.is_rotate_order_swapping_available()
