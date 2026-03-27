"""The UI actions should be added here.

No UI elements should be used, only functions manipulating the state.
"""

import contextlib
import functools

from maya import cmds
from maya.api import OpenMaya as om

from agora_community.vendor import mayax as mx
from agora_community import qtui, mayaui, lib, user_settings

from .. import core
from ..constants import *


class BakingChoice(object):
    """The baking choice used for popups."""

    IGNORE = 1
    BAKE = 2
    SMART_BAKE = 3
    PRESERVE_KEYS = 4
    NO_KEYS = 5


class MainState(qtui.BindableData):
    """The UI main state."""

    class BakeOptions(qtui.BindableData):
        smart = DEFAULT_BAKE_OPTION_SMART
        simulate = DEFAULT_BAKE_OPTION_SIMULATE
        use_dg = DEFAULT_BAKE_OPTION_DG

    class CtrlOptions(qtui.BindableData):
        active_type = DEFAULT_CTRL_TYPE
        active_color = DEFAULT_CTRL_COLOR

    busy = False

    operation_in_progress = None
    operation_objects = []

    selected_objects_count = 0
    selected_attributes = []

    bake_options = BakeOptions()
    ctrl_options = CtrlOptions()

    _load_settings_in_progress = False

    def on_attribute_changed(self, name, value):
        """Call when an attribute is changed."""
        self.save_settings()

    def __init__(self, **attributes):
        super(MainState, self).__init__(**attributes)

        self._settings = user_settings.Settings(
            TOOL_NAME,
            bake_options=self.bake_options.attributes,
            ctrl_options=self.ctrl_options.attributes,
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
        self._channel_box_selection_callback_id = om.MEventMessage.addEventCallback(
            'ChannelBoxLabelSelected',
            lib.weak_method_proxy(self._on_channel_box_selection),
        )

        self._on_obj_selection()
        self._on_channel_box_selection()

    def __del__(self):
        om.MEventMessage.removeCallback(self._obj_selection_callback_id)
        om.MEventMessage.removeCallback(self._channel_box_selection_callback_id)

    def load_settings(self):
        """Load the user options from a file."""
        self.bake_options = self._settings['bake_options'].as_dict()
        self.ctrl_options = self._settings['ctrl_options'].as_dict()

    def save_settings(self):
        """Save the user options to a file."""
        if self._load_settings_in_progress:
            return

        self._settings['bake_options'] = self.bake_options.attributes
        self._settings['ctrl_options'] = self.ctrl_options.attributes
        self._settings.save()

    @contextlib.contextmanager
    def init_busy(self):
        """Put the UI in busy mode."""
        self.busy = True

        qtui.QCoreApplication.instance().processEvents(qtui.QEventLoop.AllEvents, 1)

        try:
            yield
        finally:
            self.busy = False

    def _on_obj_selection(self, *_):
        self.selected_objects_count = len(cmds.ls(selection=True, objectsOnly=True))

        self._on_channel_box_selection()

        # delay the active operation update to fix redo
        cmds.evalDeferred(self._update_active_operation)

    def _on_channel_box_selection(self, *_):
        self.selected_attributes = (
            cmds.channelBox('mainChannelBox', query=True, selectedMainAttributes=True) or []
        )

    def _update_active_operation(self):
        self.operation_in_progress = core.get_active_operation()


def error_dialog(func):
    """Catch errors from decorated functions and display them in a dialog."""

    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except core.AnimLocatorBakeError:
            error_msg = (
                '<b>Baking failed!</b><br>You might have hit the <b>ESC</b> key.'
                '<br><br>Check the <b>Script Editor</b> for more details.'
            )

            qtui.QMessageBox.warning(mayaui.mayaMainWindow(), 'Anim Locator Error', error_msg)

            raise
        except Exception as error:
            error_msg = (
                'An <b>error</b> occurred:'
                '<br><b style="color: #f87f7f">{}: <i>{}</i></b>'
                '<br><br>Check the <b>Script Editor</b> for more details.'.format(
                    type(error).__name__,
                    error,
                )
            )

            qtui.QMessageBox.critical(mayaui.mayaMainWindow(), 'Anim Locator Error', error_msg)

            raise

    return func_wrapper


@contextlib.contextmanager
def log_catcher():
    """Catch the logs and display them in a dialog."""
    log_window = qtui.Window('Anim Locator Logger', parent=mayaui.mayaMainWindow())
    mayaui.addBaseStyleSheet(log_window)

    log_layout = qtui.QVBoxLayout()
    log_widget = qtui.QLogPlainTextEdit(log=[LOGGER])

    log_layout.addWidget(log_widget)

    log_window.setLayout(log_layout)
    log_window.resize(350 * qtui.SCALE_FACTOR, 200 * qtui.SCALE_FACTOR)

    try:
        yield
    finally:
        log_widget.removeLogs(LOGGER)

        if log_widget.toPlainText():
            log_window.show()
        else:
            log_window.deleteLater()


def enable_bake_option(state, name, enabled):
    # type: (MainState, str, bool) -> None
    """Enable/disable a bake option."""
    state.bake_options[name] = enabled


@error_dialog
def change_space_to_world(state, ctrl_detached=False, constraint_type=core.ConstraintType.PARENT):
    # type: (MainState, bool, int) -> None
    """Change animation space to world."""
    if not _ask_for_anim_blending_option() or not _warn_if_too_many_objects_selected():
        return

    overriden_bake_options = _ask_for_overriden_bake_options(
        smart_bake=state.bake_options.smart,
        constraint_type=constraint_type,
        ask_for_layers=False,
    )

    if overriden_bake_options is None:
        return

    with state.init_busy():
        core.anim_to_world(
            objects=None,
            ctrl_type=state.ctrl_options.active_type,
            ctrl_color=state.ctrl_options.active_color,
            ctrl_detached=ctrl_detached,
            constraint_type=constraint_type,
            bake_non_keyed=overriden_bake_options['bake_non_keyed'],
            bake_options=core.get_bake_options(
                state.bake_options.attributes,
                overriden_bake_options,
            ),
        )


@error_dialog
def change_space_to_target(state, constraint_type=core.ConstraintType.PARENT):
    # type: (MainState, int) -> None
    """Change animation space to target."""
    if not _ask_for_anim_blending_option() or not _warn_if_too_many_objects_selected():
        return

    overriden_bake_options = _ask_for_overriden_bake_options(
        smart_bake=state.bake_options.smart,
        constraint_type=constraint_type,
        ignore_last_object=True,
        ask_for_layers=False,
    )

    if overriden_bake_options is None:
        return

    with state.init_busy():
        core.anim_to_target(
            objects=None,
            ctrl_type=state.ctrl_options.active_type,
            ctrl_color=state.ctrl_options.active_color,
            constraint_type=constraint_type,
            bake_non_keyed=overriden_bake_options['bake_non_keyed'],
            bake_options=core.get_bake_options(
                state.bake_options.attributes,
                overriden_bake_options,
            ),
        )


@error_dialog
def change_space_to_local(state):
    # type: (MainState) -> None
    """Change animation space to local."""
    if not _ask_for_anim_blending_option() or not _warn_if_too_many_objects_selected():
        return

    objects = []

    for obj in mx.cmd.ls(selection=True, transforms=True):
        for ctrl in core.get_space_ctrls(obj):
            ctrl_target = ctrl.target

            if ctrl_target not in objects:
                objects.append(ctrl_target)

    overriden_bake_options = _ask_for_overriden_bake_options(
        objects,
        smart_bake=state.bake_options.smart,
        ask_for_layers=True,
        ask_for_constraints=False,
        ask_for_non_keys=False,
    )

    if overriden_bake_options is None:
        return

    with state.init_busy():
        core.anim_to_local(
            objects=None,
            bake_options=core.get_bake_options(
                state.bake_options.attributes,
                overriden_bake_options,
            ),
        )


@error_dialog
def copy_anim(state, local=False, constraint_type=core.ConstraintType.PARENT):
    """Copy animation from source to targets."""
    if not _ask_for_anim_blending_option() or not _warn_if_too_many_objects_selected():
        return

    if not local:
        overriden_bake_options = _ask_for_overriden_bake_options(
            ignore_first_object=True,
            ask_for_layers=True,
            ask_for_constraints=False,
            ask_for_non_keys=False,
        )

        if overriden_bake_options is None:
            return
    else:
        overriden_bake_options = {}

    with state.init_busy():
        if local:
            core.copy_anim_local(
                objects=None,
                constraint_type=constraint_type,
            )
        else:
            core.copy_anim_world(
                objects=None,
                constraint_type=constraint_type,
                bake_options=core.get_bake_options(
                    state.bake_options.attributes,
                    overriden_bake_options,
                ),
            )


@error_dialog
def swap_attribute(state, selected_objects, attr_name, attr_value):
    # type: (MainState, list[mx.Node], str, object) -> None
    """Swap the value of the selected attribute while preserving the motion."""
    if not _ask_for_anim_blending_option() or not _warn_if_too_many_objects_selected():
        return

    overriden_bake_options = _ask_for_overriden_bake_options(
        selected_objects,
        smart_bake=state.bake_options.smart,
    )

    if overriden_bake_options is None:
        return

    with state.init_busy():
        with log_catcher():
            core.swap_attribute(
                selected_objects,
                attr_name,
                attr_value,
                bake_non_keyed=overriden_bake_options['bake_non_keyed'],
                bake_options=core.get_bake_options(
                    state.bake_options.attributes,
                    overriden_bake_options,
                ),
            )


@error_dialog
def swap_rotate_order(state, selected_objects, rotate_order):
    # type: (MainState, list[mx.Node], int) -> None
    """Swap the rotation order while preserving the motion."""
    if not _ask_for_anim_blending_option() or not _warn_if_too_many_objects_selected():
        return

    overriden_bake_options = _ask_for_overriden_bake_options(
        selected_objects,
        smart_bake=state.bake_options.smart,
    )

    if overriden_bake_options is None:
        return

    with state.init_busy():
        with log_catcher():
            core.swap_rotate_order(
                selected_objects,
                rotate_order,
                bake_non_keyed=overriden_bake_options['bake_non_keyed'],
                bake_options=core.get_bake_options(
                    state.bake_options.attributes,
                    overriden_bake_options,
                ),
            )


@error_dialog
def initiate_operation(state, operation):
    # type: (MainState, core.OperationType) -> None
    """Initiate a multi-step operation."""
    if not _ask_for_anim_blending_option() or not _warn_if_too_many_objects_selected():
        return

    state.operation_objects = mx.cmd.ls(selection=True, transforms=True)

    core.initiate_operation(
        operation,
        None,
        state.ctrl_options.active_type,
        state.ctrl_options.active_color,
    )

    state.operation_in_progress = core.get_active_operation()


@error_dialog
def apply_operation(state):
    # type: (MainState) -> None
    """Apply the active multi-step operation."""
    overriden_bake_options = _ask_for_overriden_bake_options(
        state.operation_objects,
        smart_bake=state.bake_options.smart,
    )

    if overriden_bake_options is None:
        cancel_operation(state)
        return

    params = {
        'bake_non_keyed': overriden_bake_options['bake_non_keyed'],
        'bake_options': core.get_bake_options(
            state.bake_options.attributes,
            overriden_bake_options,
        ),
    }

    with state.init_busy():
        core.apply_operation(**params)

    state.operation_in_progress = core.get_active_operation()


@error_dialog
def cancel_operation(state):
    # type: (MainState) -> None
    """Cancel the active multi-step operation."""
    core.cancel_operation()

    state.operation_in_progress = core.get_active_operation()


@error_dialog
def change_ctrls_color(state, color_index):
    # type: (MainState, int) -> None
    """Change the controls' color."""
    state.ctrl_options.active_color = color_index

    core.change_ctrls_color(None, color_index)


def _ask_for_anim_blending_option():
    if cmds.optionVar(query='animBlendingOpt') == 1:  # always blend
        return True

    msg = 'The <b>animation blending</b> should be set to <b>always blend</b>.'

    fix_btn = qtui.QPushButton('Fix')
    cancel_btn = qtui.QPushButton('Cancel')

    msg_box = qtui.QMessageBox(mayaui.mayaMainWindow())
    msg_box.setIcon(qtui.QMessageBox.Warning)
    msg_box.setWindowTitle('Anim Locator Warning')
    msg_box.setText(msg)
    msg_box.addButton(fix_btn, qtui.QMessageBox.AcceptRole)
    msg_box.addButton(cancel_btn, qtui.QMessageBox.RejectRole)
    msg_box.exec_()

    if cancel_btn is msg_box.clickedButton():
        return False

    cmds.optionVar(intValue=('animBlendingOpt', 1))

    return True


def _warn_if_too_many_objects_selected():
    objects = mx.cmd.ls(selection=True, transforms=True)

    if len(objects) > TOO_MANY_OBJECTS_COUNT:
        msg = 'You have <b>{} objects selected.</b> Continue?'.format(len(objects))

        continue_btn = qtui.QPushButton('Continue')
        cancel_btn = qtui.QPushButton('Cancel')

        msg_box = qtui.QMessageBox(mayaui.mayaMainWindow())
        msg_box.setIcon(qtui.QMessageBox.Warning)
        msg_box.setWindowTitle('Anim Locator Warning')
        msg_box.setText(msg)
        msg_box.addButton(continue_btn, qtui.QMessageBox.AcceptRole)
        msg_box.addButton(cancel_btn, qtui.QMessageBox.RejectRole)
        msg_box.exec_()

        if cancel_btn is msg_box.clickedButton():
            return False

    return True


def _ask_for_overriden_bake_options(
    objects=None,
    smart_bake=DEFAULT_BAKE_OPTION_SMART,
    constraint_type=core.ConstraintType.PARENT,
    ignore_first_object=False,
    ignore_last_object=False,
    ask_for_layers=True,
    ask_for_constraints=True,
    ask_for_non_keys=True,
):
    options = {
        'smart': smart_bake,
        'preserve_keys': False,
        'bake_non_keyed': True,
        'remove_from_layers': False,
    }

    if ask_for_layers:
        anim_layers_option = _ask_for_anim_layers_option(
            objects,
            ignore_first_object=ignore_first_object,
            ignore_last_object=ignore_last_object,
        )

        if not anim_layers_option:
            return None

        if anim_layers_option == BakingChoice.BAKE:
            options['smart'] = False
            options['remove_from_layers'] = True
        elif anim_layers_option == BakingChoice.SMART_BAKE:
            options['smart'] = True
            options['remove_from_layers'] = True
    else:
        anim_layers_option = BakingChoice.IGNORE

    if smart_bake and anim_layers_option == BakingChoice.IGNORE:
        if ask_for_constraints:
            constraints_option = _ask_for_constraints_option(
                objects,
                constraint_type=constraint_type,
                ignore_last_object=ignore_last_object,
            )

            if not constraints_option:
                return None

            if constraints_option == BakingChoice.BAKE:
                options['smart'] = False
            elif constraints_option == BakingChoice.PRESERVE_KEYS:
                options['preserve_keys'] = True

        if ask_for_non_keys and (
            not ask_for_constraints or constraints_option == BakingChoice.IGNORE
        ):
            non_keyed_option = _ask_for_bake_non_keyed(
                objects,
                constraint_type=constraint_type,
                ignore_last_object=ignore_last_object,
            )

            if not non_keyed_option:
                return None

            if non_keyed_option == BakingChoice.BAKE:
                options['smart'] = False
            elif non_keyed_option == BakingChoice.NO_KEYS:
                options['bake_non_keyed'] = False

    return options


def _ask_for_bake_non_keyed(
    objects=None,
    constraint_type=core.ConstraintType.PARENT,
    ignore_last_object=False,
):
    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    if ignore_last_object and objects:
        objects.pop()

    for obj in objects:
        if not core.has_keys(obj, attributes=core.constraint_attributes(constraint_type)):
            break
    else:
        return BakingChoice.IGNORE

    bake_btn = qtui.QPushButton('Bake')
    smart_bake_btn = qtui.QPushButton('Smart Bake')
    no_keys_btn = qtui.QPushButton('No Keys')
    cancel_btn = qtui.QPushButton('Cancel')

    msg = (
        '<b>Some of the selected objects have no keys</b>.'
        '<br><br>Would you like to <b>bake</b> the locators,'
        '<br>or leave them with <b>no keys</b>?'
    )

    msg_box = qtui.QMessageBox(mayaui.mayaMainWindow())
    msg_box.setIcon(qtui.QMessageBox.Warning)
    msg_box.setWindowTitle('Anim Locator Warning')
    msg_box.setText(msg)
    msg_box.addButton(bake_btn, qtui.QMessageBox.AcceptRole)
    msg_box.addButton(smart_bake_btn, qtui.QMessageBox.AcceptRole)
    msg_box.addButton(no_keys_btn, qtui.QMessageBox.AcceptRole)
    msg_box.addButton(cancel_btn, qtui.QMessageBox.RejectRole)
    msg_box.exec_()

    if cancel_btn is msg_box.clickedButton():
        return None

    if smart_bake_btn is msg_box.clickedButton():
        return BakingChoice.SMART_BAKE

    if no_keys_btn is msg_box.clickedButton():
        return BakingChoice.NO_KEYS

    return BakingChoice.BAKE


def _ask_for_constraints_option(
    objects=None,
    constraint_type=core.ConstraintType.PARENT,
    ignore_last_object=False,
):
    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    if ignore_last_object and objects:
        objects.pop()

    for obj in objects:
        if core.has_constraints(
            obj,
            position=core.ConstraintType.is_position(constraint_type),
            rotation=core.ConstraintType.is_rotation(constraint_type),
        ):
            break
    else:
        return BakingChoice.IGNORE

    bake_btn = qtui.QPushButton('Bake')
    smart_bake_btn = qtui.QPushButton('Smart Bake')
    preserve_keys_btn = qtui.QPushButton('Preserve Keys')
    cancel_btn = qtui.QPushButton('Cancel')

    msg = 'Some of the selected objects have <b>constraints</b>.<br/>What would you like to do?'

    msg_box = qtui.QMessageBox(mayaui.mayaMainWindow())
    msg_box.setIcon(qtui.QMessageBox.Warning)
    msg_box.setWindowTitle('Anim Locator Warning')
    msg_box.setText(msg)
    msg_box.addButton(bake_btn, qtui.QMessageBox.AcceptRole)
    msg_box.addButton(smart_bake_btn, qtui.QMessageBox.AcceptRole)
    msg_box.addButton(preserve_keys_btn, qtui.QMessageBox.AcceptRole)
    msg_box.addButton(cancel_btn, qtui.QMessageBox.RejectRole)
    msg_box.exec_()

    if cancel_btn is msg_box.clickedButton():
        return None

    if smart_bake_btn is msg_box.clickedButton():
        return BakingChoice.SMART_BAKE

    if preserve_keys_btn is msg_box.clickedButton():
        return BakingChoice.PRESERVE_KEYS

    return BakingChoice.BAKE


def _ask_for_anim_layers_option(
    objects=None,
    ignore_first_object=False,
    ignore_last_object=False,
):
    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    if ignore_first_object and objects:
        objects.pop(0)

    if ignore_last_object and objects:
        objects.pop()

    for obj in objects:
        if core.anim_layers(obj):
            break
    else:
        return BakingChoice.IGNORE

    bake_btn = qtui.QPushButton('Bake')
    smart_bake_btn = qtui.QPushButton('Smart Bake')
    ignore_btn = qtui.QPushButton('Continue')
    cancel_btn = qtui.QPushButton('Cancel')

    msg = (
        'Some of the selected objects are in <b>animation layers</b>.'
        '<br/>What would you like to do?'
    )

    msg_box = qtui.QMessageBox(mayaui.mayaMainWindow())
    msg_box.setIcon(qtui.QMessageBox.Warning)
    msg_box.setWindowTitle('Anim Locator Warning')
    msg_box.setText(msg)
    msg_box.addButton(bake_btn, qtui.QMessageBox.AcceptRole)
    msg_box.addButton(smart_bake_btn, qtui.QMessageBox.AcceptRole)
    msg_box.addButton(ignore_btn, qtui.QMessageBox.AcceptRole)
    msg_box.addButton(cancel_btn, qtui.QMessageBox.RejectRole)
    msg_box.exec_()

    if cancel_btn is msg_box.clickedButton():
        return None

    if smart_bake_btn is msg_box.clickedButton():
        return BakingChoice.SMART_BAKE

    if ignore_btn is msg_box.clickedButton():
        return BakingChoice.IGNORE

    return BakingChoice.BAKE
