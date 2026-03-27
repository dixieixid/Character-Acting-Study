"""Tool to create a motion trail."""

import os

import maya.cmds as cmds

from agora_community import (
    qtui,
    mayaui,
)

from . import core
from .constants import *


def launch():
    """Launch the Motion Trail tool."""
    LOGGER.info(f'Launching {TOOL_TITLE}...')

    MotionTrailWindow(parent=mayaui.mayaMainWindow()).show()


@mayaui.dockableWindow(launcher=launch)
class MotionTrailWindow(qtui.ToolWindow):
    """
    This motion trail tool is using the default maya trail tool, but without being connected at all to any objects.
    This tool is creating its own scriptjobs in order to feed the trail shape only when maya is idle.
    At each millisecond, it checks if Maya is idle. If idle, calculate 1 more frame's worldspace position. We are still
    idle? Then it calculates the next frame

    When dragging in viewport, deleting keys, and other user actions, the trail tool start over from current frame.
    If we're at frame 10, it calculates frame 10, then 11, then 9, then 12, then 8...
    """

    _ui_file = 'motion_trail.ui'
    _ui_file = os.path.join(RESOURCE_DIRECTORY, _ui_file)

    def __init__(self, parent=None):
        super(MotionTrailWindow, self).__init__(parent=parent)

        self.ui = qtui.loadUi(self._ui_file)

        self.layout().addWidget(self.ui)

        self.change_selection_detect_job = 0

        self.setup_ui()
        self.set_icons()

        # Bind Methods to ui elements.
        self.connect_methods()

        self.refresh_camera_list()
        self.trail = core.MotionTrailAgora()

        self.ui.checkbox_on_off.setChecked(True)
        self.toggle_trail()

    def onClose(self):
        """When closing window, delete trails and ends scriptjobs"""
        core.kill_jobs()
        self.trail.delete_trail()

    def setup_ui(self):
        self.ui.button_update.setEnabled(True)
        self.ui.checkbox_auto_update.setChecked(True)
        self.ui.button_set_tracked_object.setEnabled(False)
        self.ui.button_auto_select.setEnabled(False)
        self.ui.checkbox_auto_update.setEnabled(False)
        self.ui.button_update.setEnabled(False)
        self.ui.button_number_of_frame.setText('12')

        self.resize(400, 140)
        # sanity task: kil jobs if any are already
        core.kill_jobs()

    def set_icons(self):
        self.ui.refresh_camera_list_button.setText('')
        self.ui.refresh_camera_list_button.setIcon(qtui.loadIcon('refresh'))

    def connect_methods(self):
        """Connects methods to ui elements"""
        self.ui.checkbox_on_off.clicked.connect(self.toggle_trail)
        self.ui.button_auto_select.clicked.connect(self.auto_selection_setup)
        self.ui.button_set_tracked_object.clicked.connect(self.change_tracked_objects)
        self.ui.checkbox_auto_update.clicked.connect(self.validate_checkboxes_ui)
        self.ui.button_update.clicked.connect(self.manual_process_timeline)
        self.ui.button_number_of_frame.clicked.connect(self.toggle_fade_number)
        self.ui.refresh_camera_list_button.clicked.connect(self.refresh_camera_list)
        self.ui.combo_box_camera_list.activated.connect(self.set_matrix_reference)

    def toggle_fade_number(self):
        choices = ['3', '6', '12', '24', '48', 'all']
        current_index = choices.index(self.ui.button_number_of_frame.text())
        next_index = current_index + 1
        new_settings = choices[next_index % len(choices)]
        self.ui.button_number_of_frame.setText(new_settings)
        self.trail.set_faded_frames(new_settings)

    def auto_selection_setup(self):
        """setup UI to accept auto selection"""
        if self.ui.button_auto_select.isChecked():
            cmds.scriptJob(
                event=['SelectionChanged', self.auto_selection_execute],
                compressUndo=True,
            )
            self.ui.button_set_tracked_object.setEnabled(False)
        else:
            core.kill_auto_selection_job()
            self.ui.button_set_tracked_object.setEnabled(True)

    def auto_selection_execute(self):
        if self.ui.button_auto_select.isChecked():
            self.trail.define_object()
            self.auto_process_timeline()

    def toggle_trail(self):
        """Called when clicking ON-OFF button"""
        status = self.ui.checkbox_on_off.isChecked()
        if status:
            sel = self.trail.define_object()
            if not sel:
                self.ui.checkbox_on_off.setChecked(False)
                core.warning('Need to select an object to track')
                self.disable_ui()
            else:
                self.trail_on()
        else:
            self.disable_ui()
            self.trail.delete_trail()
            core.kill_jobs()
            self.ui.button_number_of_frame.setText('12')

    def refresh_camera_list(self):
        cameras = core.query_cameras()
        self.ui.combo_box_camera_list.clear()
        self.ui.combo_box_camera_list.addItem('world')

        for camera in cameras:
            self.ui.combo_box_camera_list.addItem(camera)

    def auto_process_timeline(self):
        """Called anytime the trail is reprocessed"""
        try:
            cmds.undoInfo(stateWithoutFlush=False)
            if self.ui.checkbox_auto_update.isChecked():
                self.manual_process_timeline()

        except ValueError:
            self.clear_condition()
            self.trail.delete_trail()
            self.disable_ui()
            core.warning("Tracked object couldn't be found. Shutting off motiontrail")
            cmds.evalDeferred(self.kill_job)

        finally:
            cmds.undoInfo(stateWithoutFlush=True, undoName='TWeener')

    def manual_process_timeline(self):
        """Called when hitting manual refresh"""
        range = self.trail.prioritize_timeline()
        self.trail.prepare_pointarray(range)

    def enable_ui(self):
        """Turning UI ON"""
        self.ui.button_set_tracked_object.setEnabled(True)
        self.ui.button_auto_select.setEnabled(True)
        self.ui.checkbox_auto_update.setEnabled(True)
        self.ui.button_update.setEnabled(True)
        self.ui.combo_box_camera_list.setEnabled(True)
        self.ui.refresh_camera_list_button.setEnabled(True)
        self.ui.button_number_of_frame.setEnabled(True)

    def disable_ui(self):
        """Shutting off UI"""
        self.ui.button_set_tracked_object.setEnabled(False)
        self.ui.button_auto_select.setEnabled(False)
        self.ui.checkbox_auto_update.setEnabled(False)
        self.ui.button_update.setEnabled(False)
        self.ui.combo_box_camera_list.setEnabled(False)
        self.ui.refresh_camera_list_button.setEnabled(False)
        self.ui.button_number_of_frame.setEnabled(False)
        self.ui.checkbox_on_off.setChecked(False)

    def trail_on(self):
        """Creating script jobs, starting to track objects..."""
        self.enable_ui()
        cmds.undoInfo(stateWithoutFlush=False)
        try:
            self.set_trackedobject()
            self.trail.delete_trail()
            self.trail.create_trail_node()
            self.trail.create_dummy_point()
            self.clear_condition()
        finally:
            cmds.undoInfo(stateWithoutFlush=True, undoName='TWeener')

        cmds.condition(
            'run_trail_job',
            s='python("from agora_community.tool import motion_trail;motion_trail.core.run_script_job_every_n()")',
            d='idle',
        )
        cmds.scriptJob(
            ct=['run_trail_job', self.update_trail], compressUndo=True, killWithScene=True
        )
        cmds.scriptJob(
            event=['DragRelease', self.auto_process_timeline], compressUndo=True, killWithScene=True
        )
        cmds.scriptJob(
            event=['ModelPanelSetFocus', self.auto_process_timeline],
            compressUndo=True,
            killWithScene=True,
        )
        cmds.scriptJob(
            event=['graphEditorChanged', self.auto_process_timeline],
            compressUndo=True,
            killWithScene=True,
        )
        cmds.scriptJob(event=['Undo', self.update_trail], compressUndo=True, killWithScene=True)
        cmds.scriptJob(
            ct=['playingBack', self.auto_process_timeline], compressUndo=True, killWithScene=True
        )
        self.change_selection_detect_job = cmds.scriptJob(
            event=['DragRelease', self.auto_process_timeline], compressUndo=True
        )
        self.auto_process_timeline()
        self.validate_checkboxes_ui()

    def update_trail(self):
        """Mid way of update_trail, continuing if Maya was Idle"""
        toprocess = self.trail.get_range()
        if len(toprocess) != 0:
            self.trail.isIdle()

    def set_matrix_reference(self):
        """World by default, or used to set the trail in camera space"""
        camera = self.ui.combo_box_camera_list.currentText()

        # if camera doesn't exist: refresh and set back to world
        if not core.validate_camera_existance(camera) and camera != 'world':
            self.ui.combo_box_camera_list.setCurrentIndex(0)

        else:
            self.manual_process_timeline()
            self.trail.set_camera_reference(camera)
            self.change_tracked_objects()

    def validate_checkboxes_ui(self):
        """setup UI to accept auto update"""
        self.ui.button_set_tracked_object.setEnabled(not self.ui.button_auto_select.isChecked())
        self.ui.button_update.setEnabled(not self.ui.checkbox_auto_update.isChecked())

        if not self.ui.checkbox_on_off.isChecked():
            self.disable_ui

    def change_tracked_objects(self):
        """
        called when manually clicking change objects
        """
        objects = self.trail.define_object()
        self.trail.create_dummy_point()
        if not objects:
            self.ui.checkbox_on_off.setChecked(False)
        self.manual_process_timeline()

    def set_trackedobject(self):
        """called when turning on the UI"""
        objects = self.trail.define_object()
        if not objects:
            self.ui.checkbox_on_off.setChecked(False)

    @staticmethod
    def clear_condition():
        """Can't check if conditions exist, so we just try deleting it"""
        try:
            cmds.condition('run_trail_job', delete=True)
        except RuntimeError:
            # condition does not exist
            pass

    def kill_job(args):
        core.kill_jobs()
