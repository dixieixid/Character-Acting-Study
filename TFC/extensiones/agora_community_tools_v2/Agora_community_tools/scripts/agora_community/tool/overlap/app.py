"""Tool to create animation overlap by offsetting the curves."""

import functools

from maya import cmds
from maya.api import OpenMaya as om

from agora_community import (
    qtui,
    lib,
    mayalib,
    mayaui,
    user_settings,
)

from . import core
from .constants import *


def launch():
    """Launch the Overlap tool."""
    LOGGER.info(f'Launching {TOOL_TITLE}...')

    OverlapWindow(parent=mayaui.mayaMainWindow()).show()


def error_dialog(func):
    """Catch errors from decorated functions and display them in a dialog."""

    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except core.OverlapError as error:
            qtui.QMessageBox.warning(mayaui.mayaMainWindow(), 'Overlap Warning', str(error))
        except Exception as error:
            error_msg = (
                'An <b>error</b> occurred:'
                '<br><b style="color: #f87f7f">{}: <i>{}</i></b>'
                '<br><br>Check the <b>Script Editor</b> for more details.'.format(
                    type(error).__name__,
                    error,
                )
            )

            qtui.QMessageBox.critical(mayaui.mayaMainWindow(), 'Overlap Error', error_msg)

            raise error

    return func_wrapper


class MainState(qtui.BindableData):
    """The UI main state."""

    class BakeOptions(qtui.BindableData):
        simulate = DEFAULT_BAKE_OPTION_SIMULATE
        use_dg = DEFAULT_BAKE_OPTION_DG

    frame_offset = 1.0
    selected_objects_count = 0

    bake_options = BakeOptions()

    _load_settings_in_progress = False

    def __init__(self, **attributes):
        super(MainState, self).__init__(**attributes)

        self._settings = user_settings.Settings(
            TOOL_NAME,
            bake_options=self.bake_options.attributes,
        )

        try:
            self._load_settings_in_progress = True
            self.load_settings()
        finally:
            self._load_settings_in_progress = False

        self._obj_selection_callback_id = om.MEventMessage.addEventCallback(
            'SelectionChanged',
            lib.weak_method_proxy(self._on_obj_selection),
        )

        self._on_obj_selection()

    def __del__(self):
        om.MEventMessage.removeCallback(self._obj_selection_callback_id)

    def on_attribute_changed(self, name, value):
        """Call when an attribute is changed."""
        self.save_settings()

    def refresh(self):
        """Update the UI."""
        with mayalib.undo_skip():
            self._on_obj_selection()

    def load_settings(self):
        """Load the user options from a file."""
        self.bake_options = self._settings['bake_options'].as_dict()

    def save_settings(self):
        """Save the user options to a file."""
        if self._load_settings_in_progress:
            return

        self._settings['bake_options'] = self.bake_options.attributes
        self._settings.save()

    def _on_obj_selection(self, *_):
        self.selected_objects_count = len(cmds.ls(selection=True, objectsOnly=True))


@mayaui.dockableWindow(launcher=launch, initialWidth=250, initialHeight=75)
class OverlapWindow(qtui.ToolWindow):
    """Main window for Overlap tool."""

    def __init__(self, parent=None):
        # Add before super() to have state available inside `onMenuBar`.
        self.state = MainState()

        super(OverlapWindow, self).__init__(TOOL_TITLE, parent)

        mayaui.addBaseStyleSheet(self)

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
            action.toggled.connect(functools.partial(self._enable_bake_option, option_name))

    def _create_ui(self):
        """Create the UI."""
        state = self.state

        with self.layout() as main_layout:
            main_layout.setContentsMargins(
                4 * qtui.SCALE_FACTOR,
                4 * qtui.SCALE_FACTOR,
                4 * qtui.SCALE_FACTOR,
                4 * qtui.SCALE_FACTOR,
            )
            main_layout.setSpacing(5 * qtui.SCALE_FACTOR)

            with qtui.QFormLayout() as form_layout:
                form_layout.setHorizontalSpacing(6 * qtui.SCALE_FACTOR)

                with qtui.Slider(-5.0, 5.0) as frame_offset_field:
                    qtui.bind(frame_offset_field, state, 'frame_offset')
                    qtui.bind_callback(
                        state,
                        'frame_offset',
                        lib.weak_method_proxy(self._on_frame_offset_changed),
                    )
                    qtui.bind_activation(
                        frame_offset_field,
                        state,
                        'selected_objects_count',
                        display_processor=lambda _value: core.is_overlap_removal_available(),
                    )

                form_layout.addRow('Frame Offset', frame_offset_field)

            with qtui.QHBoxLayout():
                with qtui.QPushButton('Create') as btn:
                    btn.clicked.connect(self._on_create_overlap)
                    qtui.bind_activation(
                        btn,
                        state,
                        'selected_objects_count',
                        display_processor=lambda _value: core.is_overlap_creation_available(),
                    )

                with qtui.QPushButton('Remove') as btn:
                    btn.clicked.connect(self._on_remove_overlap)
                    qtui.bind_activation(
                        btn,
                        state,
                        'selected_objects_count',
                        display_processor=lambda _value: core.is_overlap_removal_available(),
                    )

                with qtui.ContextMenuButton('Bake') as btn:
                    menu = qtui.QMenu(btn)
                    menu.addAction(
                        'Bake to Anim Layer',
                        functools.partial(self._on_bake_overlap, to_anim_layer=True),
                    )

                    btn.setMenu(menu)
                    btn.clicked.connect(self._on_bake_overlap)
                    qtui.bind_activation(
                        btn,
                        state,
                        'selected_objects_count',
                        display_processor=lambda _value: core.is_overlap_baking_available(),
                    )

    def _enable_bake_option(self, name, enabled):
        self.state.bake_options[name] = enabled

    @error_dialog
    def _on_create_overlap(self):
        core.create_overlap(
            frame_offset=self.state.frame_offset,
            bake_options=self.state.bake_options.attributes,
        )

    @error_dialog
    def _on_bake_overlap(self, to_anim_layer=False):
        core.bake_overlap(
            frame_offset=self.state.frame_offset,
            bake_options=self.state.bake_options.attributes,
            to_anim_layer=to_anim_layer,
        )

        self.state.refresh()

    @error_dialog
    def _on_remove_overlap(self):
        core.remove_overlap()

        self.state.refresh()

    @error_dialog
    def _on_frame_offset_changed(self, frame_offset):
        core.update_overlap(frame_offset=frame_offset)
