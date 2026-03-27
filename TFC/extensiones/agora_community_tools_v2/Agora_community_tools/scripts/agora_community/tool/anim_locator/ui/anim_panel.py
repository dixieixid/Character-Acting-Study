"""The UI for the animation copying."""

from agora_community import qtui

from .. import core
from . import main


def create_anim_panel(state):
    # type: (main.MainState) -> qtui.QWidget
    """Create the UI for the animation copying."""
    with qtui.GroupVBox('Source to Target(s)', collapsed=True) as main_box:
        main_box.setToolTip('Copy animation to other objects.')
        main_box.layout().setContentsMargins(
            4 * qtui.SCALE_FACTOR,
            4 * qtui.SCALE_FACTOR,
            4 * qtui.SCALE_FACTOR,
            4 * qtui.SCALE_FACTOR,
        )
        main_box.layout().setSpacing(2 * qtui.SCALE_FACTOR)

        qtui.addStyleClass(main_box, 'section')

        with qtui.ContextMenuButton('Copy World') as btn:
            menu = qtui.QMenu(btn)
            menu.addAction(
                'Translation - Only',
                lambda: main.copy_anim(state, constraint_type=core.ConstraintType.POSITION),
            )
            menu.addAction(
                'Rotation - Only',
                lambda: main.copy_anim(state, constraint_type=core.ConstraintType.ROTATION),
            )

            btn.setMenu(menu)
            btn.setToolTip('Copy world animation.')
            btn.clicked.connect(lambda: main.copy_anim(state))

            qtui.bind_activation(
                btn,
                state,
                'selected_objects_count',
                display_processor=lambda _value: _should_enable_copy_button(state),
            )
            qtui.bind_activation(
                btn,
                state,
                'operation_in_progress',
                display_processor=lambda _value: _should_enable_copy_button(state),
            )

        with qtui.ContextMenuButton('Copy Keys') as btn:
            menu = qtui.QMenu(btn)
            menu.addAction(
                'Translation - Only',
                lambda: main.copy_anim(
                    state,
                    local=True,
                    constraint_type=core.ConstraintType.POSITION,
                ),
            )
            menu.addAction(
                'Rotation - Only',
                lambda: main.copy_anim(
                    state,
                    local=True,
                    constraint_type=core.ConstraintType.ROTATION,
                ),
            )

            btn.setMenu(menu)
            btn.setToolTip('Copy local animation.')
            btn.clicked.connect(lambda: main.copy_anim(state, local=True))

            qtui.bind_activation(
                btn,
                state,
                'selected_objects_count',
                display_processor=lambda _value: _should_enable_copy_button(state),
            )
            qtui.bind_activation(
                btn,
                state,
                'operation_in_progress',
                display_processor=lambda _value: _should_enable_copy_button(state),
            )

    return main_box


def _should_enable_copy_button(state):
    # type: (main.MainState) -> bool
    return not state.operation_in_progress and core.is_copy_anim_available()
