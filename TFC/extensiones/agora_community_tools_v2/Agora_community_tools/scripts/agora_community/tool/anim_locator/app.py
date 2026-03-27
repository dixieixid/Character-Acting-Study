"""Tool to edit animation using locators."""

from functools import partial

from agora_community import qtui, mayaui

from .ui import main
from .ui.anim_panel import create_anim_panel
from .ui.ctrls_panel import create_ctrls_panel
from .ui.space_panel import create_space_panel
from .ui.attr_swapper_panel import create_attr_swapper_panel
from .ui.scene_locators_panel import create_scene_locators_panel

from .constants import *


def launch():
    """Launch the Anim Locator tool."""
    LOGGER.info(f'Launching {TOOL_TITLE}...')

    AnimLocatorWindow(parent=mayaui.mayaMainWindow()).show()


@mayaui.dockableWindow(launcher=launch, initialWidth=150, initialHeight=190)
class AnimLocatorWindow(qtui.ToolWindow):
    """Main window for Anim Locator tool."""

    def __init__(self, parent=None):
        # Add before super() to have state available inside `onMenuBar`.
        self.state = main.MainState()

        super(AnimLocatorWindow, self).__init__(TOOL_TITLE, parent)

        mayaui.addBaseStyleSheet(self)
        qtui.addStyleSheet(self, TOOL_STYLE_PATH)

        self._busy_overlay = qtui.BusyOverlay(self)

        self.setMinimumWidth(150 * qtui.SCALE_FACTOR)
        self._create_ui()

    def onMenuBar(self, menu_bar):
        options_menu = menu_bar.addMenu('Options')

        for option_name, option_title in [
            ('simulate', 'Run Simulation'),
            ('use_dg', 'Use DG Evaluation'),
        ]:
            action = options_menu.addAction(option_title)
            action.setCheckable(True)
            action.setChecked(self.state.bake_options[option_name])
            action.toggled.connect(partial(main.enable_bake_option, self.state, option_name))

    def _create_ui(self):
        """Create the UI."""
        state = self.state

        qtui.bind_visibility(self._busy_overlay, state, 'busy')

        with self.layout() as main_layout:
            main_layout.setContentsMargins(0, 0, 0, 0)

            with qtui.ScrollVBox() as scroll_box:
                scroll_box.layout().setContentsMargins(
                    4 * qtui.SCALE_FACTOR,
                    2,
                    4 * qtui.SCALE_FACTOR,
                    4 * qtui.SCALE_FACTOR,
                )
                scroll_box.layout().setSpacing(2 * qtui.SCALE_FACTOR)

                create_ctrls_panel(state)

                with qtui.QHBoxLayout() as layout:
                    layout.setContentsMargins(
                        8 * qtui.SCALE_FACTOR,
                        2 * qtui.SCALE_FACTOR,
                        2 * qtui.SCALE_FACTOR,
                        2 * qtui.SCALE_FACTOR,
                    )

                    with qtui.QCheckBox('Bake Every Frame') as checkbox:
                        qtui.bind(
                            checkbox,
                            state.bake_options,
                            'smart',
                            value_processor=lambda value: not value,
                            display_processor=lambda value: not value,
                        )

                create_space_panel(state)
                create_anim_panel(state)
                create_attr_swapper_panel(state)
                create_scene_locators_panel(state)
