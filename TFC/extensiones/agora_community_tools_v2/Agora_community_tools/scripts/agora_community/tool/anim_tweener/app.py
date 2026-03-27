"""Tool to create animation tweening."""

import os

from agora_community import (
    qtui,
    mayaui,
)

from .constants import *
from . import core


def launch():
    """Launch the Anim Tweener tool."""
    LOGGER.info(f'Launching {TOOL_TITLE}...')

    AnimTweenerWindow(parent=mayaui.mayaMainWindow()).show()


@mayaui.dockableWindow(launcher=launch)
class AnimTweenerWindow(qtui.ToolWindow):
    _ui_file = 'anim_tweener.ui'
    _ui_file = os.path.join(RESOURCE_DIRECTORY, _ui_file)
    mod = '0'
    goals = []
    autokey_pref = True
    allowed_mod = []
    AniAttr = []
    graphsel = ''

    def __init__(self, parent=None):
        super(AnimTweenerWindow, self).__init__(parent=parent)

        self.ui = qtui.loadUi(self._ui_file)

        self.layout().addWidget(self.ui)

        self.setup_ui()
        self.connect_methods()

    def setup_ui(self):
        """Additional setup for the ui widget."""
        self.ui.helpbox.hide()
        self.resize(300, 70)

    def connect_methods(self):
        """Connects methods to ui elements"""
        self.ui.slider_tweener.sliderPressed.connect(self.start_dragging)
        self.ui.slider_tweener.sliderReleased.connect(self.release_dragging)
        self.ui.slider_tweener.sliderMoved.connect(self.dragging)
        self.ui.button_help.clicked.connect(self.toggle_help)

    def start_dragging(self):
        """Signal called when we start dragging the slider"""
        if core.check_if_sel_empty():
            return
        self.autokey_pref, self.AniAttr = core.pre_opperation()
        self.mod = core.get_mods()
        self.goals, self.graphsel = core.tmt_get_tween_goals(self.mod, self.AniAttr)
        self.dragging()

    def toggle_help(self):
        visibility = self.ui.helpbox.isHidden()
        self.ui.helpbox.setHidden(not visibility)

        if visibility == False:
            self.resize(300, 70)
        else:
            self.resize(300, 170)

    def dragging(self):
        """Signal called when we're dragging the slider"""
        if core.check_if_sel_empty():
            return
        tween_value = self.ui.slider_tweener.value()
        core.tm_tweener_drag(self.goals, tween_value, self.graphsel, self.mod)

    def release_dragging(self):
        """Signal called when we're releasing the slider"""
        self.ui.slider_tweener.setValue(0)
        core.post_opperation(self.autokey_pref, self.graphsel)
