"""The UI for the control types."""

import os
from functools import partial

from agora_community import qtui

from .. import core
from ..constants import ICONS_DIRECTORY
from . import main
from . import color_panel


def create_ctrls_panel(state):
    # type: (main.MainState) -> qtui.QWidget
    """Create the UI for the control types."""
    with qtui.QWidget() as main_widget:
        qtui.addStyleClass(main_widget, 'ctrls-container')

        with qtui.QHBoxLayout() as layout:
            layout.setAlignment(qtui.Qt.AlignCenter)
            layout.setContentsMargins(
                4 * qtui.SCALE_FACTOR,
                4 * qtui.SCALE_FACTOR,
                4 * qtui.SCALE_FACTOR,
                4 * qtui.SCALE_FACTOR,
            )
            layout.setSpacing(12 * qtui.SCALE_FACTOR)

            with qtui.ToggleButton(buttonClass=qtui.TintedIconButton) as ctrl_btn:
                ctrl_btn.layout().setSpacing(6 * qtui.SCALE_FACTOR)

                for ctrl_type in core.CtrlType.all():
                    ctrl_type_name = core.CtrlType.name(ctrl_type)
                    ctrl_icon_path = os.path.join(ICONS_DIRECTORY, ctrl_type_name + '.svg')

                    btn = ctrl_btn.addState('', ctrl_type)
                    btn.setIcon(qtui.QIcon(ctrl_icon_path))
                    btn.setToolTip(ctrl_type_name.title())
                    btn.clicked.connect(partial(core.change_ctrls_type, None, ctrl_type))

                    qtui.addStyleClass(btn, 'ctrl-type-button')

                qtui.bind(ctrl_btn, state.ctrl_options, 'active_type')

            with qtui.QPushButton() as btn:
                qtui.addStyleClass(btn, 'color-swatch-button')
                color_panel.colorize_button(btn, state.ctrl_options.active_color)

                qtui.bind_callback(
                    state.ctrl_options,
                    'active_color',
                    lambda color_index: color_panel.colorize_button(btn, color_index),
                )

                btn.clicked.connect(
                    lambda: qtui.PopupPanel.open(
                        btn, partial(color_panel.create_color_panel, state)
                    )
                )

    return main_widget
