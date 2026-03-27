"""The UI for the color functionaliy."""

from functools import partial

from agora_community import qtui

from ..constants import *
from .. import core
from . import main

_COLORS_PER_ROW = 7


def create_color_panel(state, popup):
    # type: (main.MainState, qtui.PopupPanel) -> qtui.QWidget
    """Create the UI for the color functionaliy."""
    colors = [
        color_index for color_index in core.index_colors() if color_index not in CTRL_COLORS_IGNORED
    ]

    with qtui.QWidget() as main_widget:
        with qtui.QVBoxLayout() as main_layout:
            main_layout.setContentsMargins(
                4 * qtui.SCALE_FACTOR,
                4 * qtui.SCALE_FACTOR,
                4 * qtui.SCALE_FACTOR,
                4 * qtui.SCALE_FACTOR,
            )

            with qtui.QGridLayout() as color_layout:
                color_layout.setSpacing(2 * qtui.SCALE_FACTOR)

                row = -1
                column = -1

                for i, color_index in enumerate(colors):
                    if i % _COLORS_PER_ROW:
                        column += 1
                    else:
                        row += 1
                        column = 0

                    color_btn = qtui.QPushButton()
                    color_btn.clicked.connect(
                        partial(_on_color_selection, state, color_index, popup)
                    )

                    qtui.addStyleClass(color_btn, 'color-swatch-button')
                    colorize_button(color_btn, color_index)

                    color_layout.addWidget(color_btn, row, column)

    return main_widget


def colorize_button(button, color_index):
    """Set the button's background color."""
    rgb_color = [str(value) for value in core.color_index_to_rgb(color_index)]
    color_style = 'QPushButton {{ background: rgb({}); }}'.format(','.join(rgb_color))

    button.setStyleSheet(color_style)


def _on_color_selection(state, color_index, popup):
    # type: (main.MainState, int, qtui.PopupPanel) -> None
    main.change_ctrls_color(state, color_index)

    popup.close()
