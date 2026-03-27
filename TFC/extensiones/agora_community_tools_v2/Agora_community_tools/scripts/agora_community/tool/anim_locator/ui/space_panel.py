"""The UI for the animation space switching."""

from agora_community import qtui

from .. import core
from . import main


def create_space_panel(state):
    # type: (main.MainState) -> qtui.QWidget
    """Create the UI for the animation space switching."""
    with qtui.GroupVBox('Space', collapsable=False) as main_box:
        main_box.setToolTip('Copy anim to a different space.')
        main_box.layout().setContentsMargins(
            4 * qtui.SCALE_FACTOR,
            4 * qtui.SCALE_FACTOR,
            4 * qtui.SCALE_FACTOR,
            4 * qtui.SCALE_FACTOR,
        )
        main_box.layout().setSpacing(2 * qtui.SCALE_FACTOR)

        qtui.addStyleClass(main_box, 'section')

        with qtui.QWidget() as widget:
            with qtui.QHBoxLayout() as layout:
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(4 * qtui.SCALE_FACTOR)

                with qtui.QPushButton() as btn:
                    qtui.addStyleClass(btn, 'apply-button')
                    btn.clicked.connect(lambda: main.apply_operation(state))

                    qtui.bind(
                        btn,
                        state,
                        'operation_in_progress',
                        display_processor=_get_applied_operation_title,
                    )

                with qtui.IconButton('ban') as btn:
                    qtui.addStyleClass(btn, 'cancel-button')
                    btn.clicked.connect(lambda: main.cancel_operation(state))

            qtui.bind_visibility(widget, state, 'operation_in_progress')

        with qtui.ContextMenuButton('World') as btn:
            menu = qtui.QMenu(btn)
            menu.addAction(
                'Translation - Only',
                lambda: main.change_space_to_world(
                    state,
                    constraint_type=core.ConstraintType.POSITION,
                ),
            )
            menu.addAction(
                'Rotation - Only',
                lambda: main.change_space_to_world(
                    state,
                    constraint_type=core.ConstraintType.ROTATION,
                ),
            )
            menu.addSeparator()
            menu.addAction(
                'Detached',
                lambda: main.change_space_to_world(state, ctrl_detached=True),
            )
            menu.addSeparator()
            menu.addAction(
                'Different Pivot',
                lambda: main.initiate_operation(state, core.OperationType.PIVOT),
            )
            menu.addAction(
                'Aim Space',
                lambda: main.initiate_operation(state, core.OperationType.AIM),
            )

            btn.setMenu(menu)
            btn.setToolTip('Copy anim to a world space ctrl.')
            btn.clicked.connect(lambda: main.change_space_to_world(state))

            qtui.bind_activation(
                btn,
                state,
                'selected_objects_count',
                display_processor=lambda _value: _should_enable_world_button(state),
            )
            qtui.bind_invisibility(btn, state, 'operation_in_progress')

        with qtui.ContextMenuButton('Target') as btn:
            menu = qtui.QMenu(btn)
            menu.addAction(
                'Translation - Only',
                lambda: main.change_space_to_target(
                    state,
                    constraint_type=core.ConstraintType.POSITION,
                ),
            )
            menu.addAction(
                'Rotation - Only',
                lambda: main.change_space_to_target(
                    state,
                    constraint_type=core.ConstraintType.ROTATION,
                ),
            )

            btn.setMenu(menu)
            btn.setToolTip('Put Source(s) in Target space.')
            btn.clicked.connect(lambda: main.change_space_to_target(state))

            qtui.bind_activation(
                btn,
                state,
                'selected_objects_count',
                display_processor=lambda _value: _should_enable_target_button(state),
            )
            qtui.bind_activation(
                btn,
                state,
                'operation_in_progress',
                display_processor=lambda _value: _should_enable_target_button(state),
            )

        with qtui.QPushButton('Local') as btn:
            btn.setToolTip("Send world ctrl's anim back to local ctrl.")
            btn.clicked.connect(lambda: main.change_space_to_local(state))

            qtui.bind_activation(
                btn,
                state,
                'selected_objects_count',
                display_processor=lambda _value: _should_enable_local_button(state),
            )
            qtui.bind_activation(
                btn,
                state,
                'operation_in_progress',
                display_processor=lambda _value: _should_enable_local_button(state),
            )

    return main_box


def _should_enable_world_button(state):
    # type: (main.MainState) -> bool
    return not state.operation_in_progress and core.is_world_space_available()


def _should_enable_target_button(state):
    # type: (main.MainState) -> bool
    return not state.operation_in_progress and core.is_target_space_available()


def _should_enable_local_button(state):
    # type: (main.MainState) -> bool
    return not state.operation_in_progress and core.is_local_space_available()


def _get_applied_operation_title(operation):
    if operation == core.OperationType.PIVOT:
        return 'Apply Pivot(s)'

    if operation == core.OperationType.AIM:
        return 'Apply Aim Space'

    return 'Apply'
