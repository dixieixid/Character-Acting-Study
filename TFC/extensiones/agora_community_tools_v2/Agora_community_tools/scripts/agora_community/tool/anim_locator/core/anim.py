"""Animation functionality."""

import contextlib

from agora_community.vendor import mayax as mx

from ..constants import *
from .exceptions import AnimLocatorError, AnimLocatorBakeError
from .types import ConstraintType, OperationType, CtrlType
from .general import (
    get_temp_grp,
    delete_temp_grp,
    get_active_operation,
    set_active_operation,
)
from .ctrl import (
    create_ctrl,
    create_temp_ctrl,
    make_temp_ctrl_permanent,
    is_ctrl,
    is_temp_ctrl,
    all_temp_ctrls,
)
from . import utils


def get_bake_options(*options_dicts):
    """Retrieve the bake options."""
    options = {
        'smart': DEFAULT_BAKE_OPTION_SMART,
        'preserve_keys': False,
        'simulate': DEFAULT_BAKE_OPTION_SIMULATE,
        'use_dg': DEFAULT_BAKE_OPTION_DG,
        'remove_from_layers': False,
    }

    for name in options:
        for source in options_dicts:
            if name in source:
                options[name] = source[name]

    return options


@contextlib.contextmanager
def preserve_motion(
    objects,
    constraint_type=ConstraintType.PARENT,
    bake_non_keyed=True,
    bake_options=None,
):
    """Preserve the objects' motion after changing their attributes."""
    undo_name = 'preserve_motion'

    try:
        mx.cmd.undoInfo(openChunk=True, chunkName=undo_name)

        baked_time = None
        baked_attrs = constraint_attributes(constraint_type)
        temp_grp = get_temp_grp()

        ctrls = []
        constraints = []
        baked_ctrls = []
        baked_objects = []
        objects_without_keys = []

        for obj in objects:
            ctrl = mx.cmd.createNode(
                'transform',
                name=obj.name + '_baked',
                parent=temp_grp,
                skipSelect=True,
            )

            if constraint_type == ConstraintType.POSITION:
                constraint = mx.cmd.pointConstraint(obj, ctrl, maintainOffset=False)[0]
            elif constraint_type == ConstraintType.ROTATION:
                constraint = mx.cmd.orientConstraint(obj, ctrl, maintainOffset=False)[0]
            else:
                constraint = mx.cmd.parentConstraint(obj, ctrl, maintainOffset=False)[0]

            if utils.has_keys(obj, baked_attrs):
                obj_has_keys = True
            else:
                obj_has_keys = False
                objects_without_keys.append(obj)

            if obj_has_keys or bake_non_keyed:
                baked_ctrls.append(ctrl)
                baked_objects.append(obj)

            ctrls.append(ctrl)
            constraints.append(constraint)

        if baked_ctrls:
            if objects_without_keys and bake_non_keyed:
                baked_time = utils.get_time_range()
            else:
                frames_with_keys = utils.get_frames_with_keys(baked_objects, baked_attrs)
                baked_time = (frames_with_keys[0], frames_with_keys[-1])

            do_smart_baking(
                baked_ctrls,
                source_objects=baked_objects,
                time_range=baked_time,
                attributes=baked_attrs,
                bake_options=bake_options,
            )

        mx.cmd.delete(constraints)
        del constraints[:]

        yield ctrls

        for obj, ctrl in zip(objects, ctrls):
            utils.delete_constraints(
                obj,
                position=ConstraintType.is_position(constraint_type),
                rotation=ConstraintType.is_rotation(constraint_type),
            )

            if constraint_type == ConstraintType.POSITION:
                constraint = mx.cmd.pointConstraint(
                    ctrl,
                    obj,
                    maintainOffset=False,
                    skip=utils.get_locked_translate_axes(obj),
                )[0]
            elif constraint_type == ConstraintType.ROTATION:
                constraint = mx.cmd.orientConstraint(
                    ctrl,
                    obj,
                    maintainOffset=False,
                    skip=utils.get_locked_rotate_axes(obj),
                )[0]
            else:
                constraint = mx.cmd.parentConstraint(
                    ctrl,
                    obj,
                    maintainOffset=False,
                    skipTranslate=utils.get_locked_translate_axes(obj),
                    skipRotate=utils.get_locked_rotate_axes(obj),
                )[0]

            constraints.append(constraint)

        if baked_ctrls:
            do_smart_baking(
                baked_objects,
                source_objects=baked_ctrls,
                time_range=baked_time,
                attributes=baked_attrs,
                bake_options=bake_options,
            )

        mx.cmd.delete(constraints)
        mx.cmd.delete(ctrls)

        delete_temp_grp()
    finally:
        mx.cmd.undoInfo(closeChunk=True, chunkName=undo_name)


@utils.time_logger
@mx.undoable
def anim_to_world(
    objects,
    ctrl_type=DEFAULT_CTRL_TYPE,
    ctrl_color=DEFAULT_CTRL_COLOR,
    ctrl_detached=False,
    constraint_type=ConstraintType.PARENT,
    bake_non_keyed=True,
    bake_options=None,
):
    """Copy objects' animation to world space controls.

    If `objects` is `None` the selected objects will be used instead.
    """
    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    baked_attrs = constraint_attributes(constraint_type)
    current_time = mx.cmd.currentTime(query=True)

    ctrls = []
    targets = []
    targets_without_keys = []
    baked_ctrls = []
    baked_targets = []
    temp_objects = []

    is_pivot_change = False

    for obj in objects:
        if is_temp_ctrl(obj):
            ctrl = obj
            target = ctrl.target

            make_temp_ctrl_permanent(ctrl)

            is_pivot_change = True
        else:
            if not is_world_space_available([obj]):
                continue

            if ctrl_detached:
                ctrl_suffix = CTRL_SUFFIX_DETACHED
            else:
                ctrl_suffix = CTRL_SUFFIX_WORLD

            ctrl = create_ctrl(
                '{}_{}'.format(obj.name, ctrl_suffix),
                ctrl_type,
                ctrl_color,
                target=obj,
            )
            target = obj

        ctrl['rotateOrder'].keyable = True

        constraint = mx.cmd.parentConstraint(target, ctrl, maintainOffset=is_pivot_change)[0]

        if utils.has_keys(target, baked_attrs):
            target_has_keys = True
        else:
            target_has_keys = False
            targets_without_keys.append(target)

        ctrls.append(ctrl)
        targets.append(target)

        if target_has_keys or bake_non_keyed:
            baked_ctrls.append(ctrl)
            baked_targets.append(target)

        temp_objects.append(constraint)

    if not ctrls:
        return

    if baked_ctrls:
        if targets_without_keys and bake_non_keyed:
            baked_time = utils.get_time_range()
        else:
            frames_with_keys = utils.get_frames_with_keys(baked_targets, baked_attrs)
            baked_time = (frames_with_keys[0], frames_with_keys[-1])

        do_smart_baking(
            baked_ctrls,
            source_objects=baked_targets,
            time_range=baked_time,
            attributes=baked_attrs,
            bake_options=bake_options,
        )

    mx.cmd.delete(temp_objects)

    if ctrl_detached:
        for ctrl in ctrls:
            ctrl.target = None
    else:
        for i, ctrl in enumerate(ctrls):
            ctrl_target = targets[i]

            utils.delete_constraints(
                ctrl_target,
                position=ConstraintType.is_position(constraint_type),
                rotation=ConstraintType.is_rotation(constraint_type),
            )

            if constraint_type == ConstraintType.POSITION:
                mx.cmd.pointConstraint(
                    ctrl,
                    ctrl_target,
                    maintainOffset=False,
                    skip=utils.get_locked_translate_axes(ctrl_target),
                )
                mx.cmd.orientConstraint(ctrl_target, ctrl, maintainOffset=False)

                utils.lock_rotation_attributes(ctrl)
            elif constraint_type == ConstraintType.ROTATION:
                mx.cmd.orientConstraint(
                    ctrl,
                    ctrl_target,
                    maintainOffset=False,
                    skip=utils.get_locked_rotate_axes(ctrl_target),
                )
                mx.cmd.pointConstraint(ctrl_target, ctrl, maintainOffset=False)

                utils.lock_position_attributes(ctrl)
            else:
                if is_pivot_change:
                    frames_with_keys = utils.get_frames_with_keys([ctrl], baked_attrs)

                    if frames_with_keys:
                        # change to a frame with keys to avoid issues when maintaining the offset
                        mx.cmd.currentTime(frames_with_keys[0])

                mx.cmd.parentConstraint(
                    ctrl,
                    ctrl_target,
                    maintainOffset=is_pivot_change,
                    skipTranslate=utils.get_locked_translate_axes(ctrl_target),
                    skipRotate=utils.get_locked_rotate_axes(ctrl_target),
                )

    mx.cmd.currentTime(current_time)
    mx.cmd.select(ctrls)


@utils.time_logger
@mx.undoable
def anim_to_target(
    objects,
    ctrl_type=DEFAULT_CTRL_TYPE,
    ctrl_color=DEFAULT_CTRL_COLOR,
    constraint_type=ConstraintType.PARENT,
    bake_non_keyed=True,
    bake_options=None,
):
    """Put the objects' animation into the space of the last selected object.

    If `objects` is `None` the selected objects will be used instead.
    """
    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    if not is_target_space_available(objects):
        return

    baked_attrs = constraint_attributes(constraint_type)
    master = objects[-1]

    ctrls = []
    targets = []
    targets_without_keys = []
    baked_ctrls = []
    baked_targets = []
    temp_objects = []

    for obj in objects[:-1]:
        if get_space_ctrls(obj):
            continue

        ctrl = create_ctrl(
            '{}_{}'.format(obj.name, CTRL_SUFFIX_TARGET),
            ctrl_type,
            ctrl_color,
            target=obj,
            with_buffer=True,
        )
        ctrl['rotateOrder'].keyable = True

        target = obj

        if constraint_type == ConstraintType.POSITION:
            mx.cmd.pointConstraint(master, ctrl.buffer, maintainOffset=False)
        elif constraint_type == ConstraintType.ROTATION:
            mx.cmd.orientConstraint(master, ctrl.buffer, maintainOffset=False)
        else:
            mx.cmd.parentConstraint(master, ctrl.buffer, maintainOffset=False)

        constraint = mx.cmd.parentConstraint(target, ctrl, maintainOffset=False)[0]

        if utils.has_keys(target, baked_attrs):
            target_has_keys = True
        else:
            target_has_keys = False
            targets_without_keys.append(target)

        ctrls.append(ctrl)
        targets.append(target)

        if target_has_keys or bake_non_keyed:
            baked_ctrls.append(ctrl)
            baked_targets.append(target)

        temp_objects.append(constraint)

    if not ctrls:
        return

    if baked_ctrls:
        if targets_without_keys and bake_non_keyed:
            baked_time = utils.get_time_range()
        else:
            frames_with_keys = utils.get_frames_with_keys(baked_targets, baked_attrs)
            baked_time = (frames_with_keys[0], frames_with_keys[-1])

        do_smart_baking(
            baked_ctrls,
            source_objects=baked_targets,
            time_range=baked_time,
            attributes=baked_attrs,
            bake_options=bake_options,
        )

    mx.cmd.delete(temp_objects)

    for i, ctrl in enumerate(ctrls):
        ctrl_target = targets[i]

        utils.delete_constraints(
            ctrl_target,
            position=ConstraintType.is_position(constraint_type),
            rotation=ConstraintType.is_rotation(constraint_type),
        )

        if constraint_type == ConstraintType.POSITION:
            mx.cmd.pointConstraint(
                ctrl,
                ctrl_target,
                maintainOffset=False,
                skip=utils.get_locked_translate_axes(ctrl_target),
            )
            mx.cmd.orientConstraint(ctrl_target, ctrl, maintainOffset=False)

            utils.lock_rotation_attributes(ctrl)
        elif constraint_type == ConstraintType.ROTATION:
            mx.cmd.orientConstraint(
                ctrl,
                ctrl_target,
                maintainOffset=False,
                skip=utils.get_locked_rotate_axes(ctrl_target),
            )
            mx.cmd.pointConstraint(ctrl_target, ctrl, maintainOffset=False)

            utils.lock_position_attributes(ctrl)
        else:
            mx.cmd.parentConstraint(
                ctrl,
                ctrl_target,
                maintainOffset=False,
                skipTranslate=utils.get_locked_translate_axes(ctrl_target),
                skipRotate=utils.get_locked_rotate_axes(ctrl_target),
            )

        utils.lock_transform_attributes(ctrl.buffer)

    mx.cmd.select(ctrls)


@utils.time_logger
@mx.undoable
def anim_to_local(objects, bake_options=None):
    """Copy objects' animation from world/target space controls.

    If `objects` is `None` the selected objects will be used instead.
    """
    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    baked_attrs = constraint_attributes(ConstraintType.PARENT)

    ctrls = []
    ctrls_without_keys = []
    targets = []

    for obj in objects:
        if not is_local_space_available([obj]):
            continue

        space_ctrls = get_space_ctrls(obj)

        for ctrl in space_ctrls:
            target = ctrl.target

            if ctrl in ctrls:
                continue

            ctrls.append(ctrl)

            if target not in targets:
                targets.append(target)

            if not utils.has_keys(ctrl, baked_attrs):
                target_frames_with_keys = utils.get_frames_with_keys(
                    [target],
                    attributes=baked_attrs,
                )

                if target_frames_with_keys:
                    mx.cmd.setKeyframe(ctrl, time=target_frames_with_keys, attribute=baked_attrs)
                else:
                    ctrls_without_keys.append(ctrl)

    if not ctrls:
        return

    if targets:
        if ctrls_without_keys:
            baked_time = utils.get_time_range()
        else:
            frames_with_keys = utils.get_frames_with_keys(ctrls, attributes=baked_attrs)
            baked_time = (frames_with_keys[0], frames_with_keys[-1])

        do_smart_baking(
            targets,
            source_objects=ctrls,
            time_range=baked_time,
            attributes=baked_attrs,
            bake_options=bake_options,
        )

    for ctrl in ctrls:
        ctrl_buffer = ctrl.buffer

        if ctrl_buffer:
            ctrl_buffer.delete()
        else:
            ctrl.delete()

    mx.cmd.select(targets)


@utils.time_logger
@mx.undoable
def copy_anim_world(objects, constraint_type=ConstraintType.PARENT, bake_options=None):
    """Copy the first object's world animation to the other objects.

    If `objects` is `None` the selected objects will be used instead.
    """
    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    if not is_copy_anim_available(objects, constraint_type):
        return

    baked_attrs = constraint_attributes(constraint_type)

    source = objects[0]
    targets = objects[1:]
    temp_objects = []

    for target in targets:
        mx.cmd.cutKey(target, clear=True, attribute=baked_attrs)

        utils.delete_constraints(
            target,
            position=ConstraintType.is_position(constraint_type),
            rotation=ConstraintType.is_rotation(constraint_type),
        )

        if constraint_type == ConstraintType.POSITION:
            constraint = mx.cmd.pointConstraint(
                source,
                target,
                maintainOffset=False,
                skip=utils.get_locked_translate_axes(target),
            )[0]
        elif constraint_type == ConstraintType.ROTATION:
            constraint = mx.cmd.orientConstraint(
                source,
                target,
                maintainOffset=False,
                skip=utils.get_locked_rotate_axes(target),
            )[0]
        else:
            constraint = mx.cmd.parentConstraint(
                source,
                target,
                maintainOffset=False,
                skipTranslate=utils.get_locked_translate_axes(target),
                skipRotate=utils.get_locked_rotate_axes(target),
            )[0]

        temp_objects.append(constraint)

    source_frames_with_keys = utils.get_frames_with_keys([source], attributes=baked_attrs)
    baked_time = (source_frames_with_keys[0], source_frames_with_keys[-1])

    do_smart_baking(
        targets,
        source_objects=[source],
        time_range=baked_time,
        attributes=baked_attrs,
        bake_options=bake_options,
    )

    mx.cmd.delete(temp_objects)


@utils.time_logger
@mx.undoable
def copy_anim_local(objects, constraint_type=ConstraintType.PARENT):
    """Copy the first object's local animation to the other objects.

    If `objects` is `None` the selected objects will be used instead.
    """
    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    if not is_copy_anim_available(objects, constraint_type):
        return

    anim_attributes = constraint_attributes(constraint_type)

    source = objects[0]
    targets = objects[1:]

    mx.cmd.copyKey(source, attribute=anim_attributes)

    for target in targets:
        mx.cmd.cutKey(target, clear=True, attribute=anim_attributes)
        mx.cmd.pasteKey(target, attribute=anim_attributes)


@utils.time_logger
@mx.undoable
def swap_attribute(
    objects,
    attr_name,
    attr_value,
    bake_non_keyed=True,
    bake_options=None,
):
    """Swap the value of the selected attribute while preserving the motion.

    If `objects` is `None` the selected objects will be used instead.
    """
    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    if not objects:
        return

    valid_objects = []
    failed_objects = []

    for obj in objects:
        try:
            attr = obj[attr_name]
        except mx.MayaAttributeError:
            attr = None

        attr_value_valid = attr and utils.is_attribute_value_valid(obj, attr_name, attr_value)

        if attr_value_valid and is_attribute_swapping_available([obj], attr_name):
            valid_objects.append(obj)
        else:
            if not attr:
                fail_info = 'attribute does not exist'
            elif not attr_value_valid:
                fail_info = 'wrong attribute value'
            elif attr.locked:
                fail_info = 'attribute is locked'
            elif get_space_ctrls(obj):
                fail_info = 'is connected to a space control'
            else:
                fail_info = '???'

            failed_objects.append((obj, fail_info))

    with preserve_motion(
        valid_objects,
        bake_non_keyed=bake_non_keyed,
        bake_options=bake_options,
    ):
        for obj in valid_objects:
            obj_attr = obj[attr_name]

            if obj_attr.type == 'enum' and isinstance(attr_value, str):
                attr_value = utils.get_enum_values(obj, attr_name).index(attr_value)

            obj_attr.value = attr_value

            mx.cmd.keyframe(obj_attr, edit=True, valueChange=attr_value)

    if failed_objects:
        LOGGER.warning(
            '"%s" attribute swapping failed for:\n%s',
            attr_name,
            '\n'.join(
                '{} - {}'.format(obj.uniqueName, fail_info) for obj, fail_info in failed_objects
            ),
        )

        mx.cmd.select([obj for obj, _fail_info in failed_objects])


@utils.time_logger
@mx.undoable
def swap_rotate_order(
    objects,
    rotate_order,
    bake_non_keyed=True,
    bake_options=None,
):
    """Swap the rotation order while preserving the motion.

    If `objects` is `None` the selected objects will be used instead.
    """
    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    if not objects:
        return

    valid_objects = []
    failed_objects = []
    objects_with_locked_rotation = []

    for obj in objects:
        if is_rotate_order_swapping_available([obj]):
            valid_objects.append(obj)

            locked_rotate_axes = utils.get_locked_rotate_axes(obj)

            if locked_rotate_axes:
                objects_with_locked_rotation.append((obj, ', '.join(locked_rotate_axes)))
        else:
            rotate_order_attr = utils.find_connected_source_attribute(obj['rotateOrder'])

            if rotate_order_attr.locked:
                fail_info = 'rotate order attribute is locked'
            elif get_space_ctrls(obj):
                fail_info = 'is connected to a space control'
            else:
                fail_info = '???'

            failed_objects.append((obj, fail_info))

    with preserve_motion(
        valid_objects,
        constraint_type=ConstraintType.ROTATION,
        bake_non_keyed=bake_non_keyed,
        bake_options=bake_options,
    ):
        for obj in valid_objects:
            rotate_order_attr = utils.find_connected_source_attribute(obj['rotateOrder'])
            rotate_order_attr.value = rotate_order

            mx.cmd.keyframe(rotate_order_attr, edit=True, valueChange=rotate_order)

    if failed_objects:
        LOGGER.warning(
            'Rotate order swapping failed for:\n%s',
            '\n'.join(
                '{} - {}'.format(obj.uniqueName, fail_info) for obj, fail_info in failed_objects
            ),
        )

        mx.cmd.select([obj for obj, _fail_info in failed_objects])

    if objects_with_locked_rotation:
        LOGGER.info(
            'Rotate order swapping may have not worked because:\n%s',
            '\n'.join(
                '{} - Rotate axes locked: {}'.format(obj.uniqueName, info)
                for obj, info in objects_with_locked_rotation
            ),
        )


def is_world_space_available(objects=None):
    """Check if any of the objects can be changed to world space.

    If `objects` is `None` the selected objects will be used instead.
    """
    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    for obj in objects:
        if not get_space_ctrls(obj):
            return True

    return False


def is_target_space_available(objects=None):
    """Check if any of the objects can be changed to target space.

    If `objects` is `None` the selected objects will be used instead.
    """
    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    valid_objects = []

    for obj in objects:
        if not get_space_ctrls(obj) or obj == objects[-1]:
            valid_objects.append(obj)

    return len(valid_objects) > 1


def is_local_space_available(objects=None):
    """Check if any of the objects can be changed to local space.

    If `objects` is `None` the selected objects will be used instead.
    """
    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    for obj in objects:
        if get_space_ctrls(obj):
            return True

    return False


def is_copy_anim_available(objects=None, constraint_type=ConstraintType.PARENT):
    """Check if it's possible to copy animation between objects.

    If `objects` is `None` the selected objects will be used instead.
    """
    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    anim_attributes = constraint_attributes(constraint_type)

    if len(objects) > 1 and utils.has_keys(objects[0], anim_attributes):
        return True

    return False


def is_attribute_swapping_available(objects=None, attr_name=None):
    """Check if any of the objects can have their attribute swapped.

    If `objects` is `None` the selected objects will be used instead.
    If `attr_name` is `None` the selected attribute in the channel box will be used instead.
    """
    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    if attr_name is None:
        attrs = mx.cmd.channelBox('mainChannelBox', query=True, selectedMainAttributes=True) or []

        if len(attrs) != 1:
            return False

        attr_name = attrs[0]

    for obj in objects:
        try:
            attr_settable = mx.cmd.getAttr(obj[attr_name], settable=True)
        except mx.MayaAttributeError:
            continue

        if attr_settable and (is_ctrl(obj) or not get_space_ctrls(obj)):
            return True

    return False


def is_rotate_order_swapping_available(objects=None):
    """Check if any of the objects can have their rotate order swapped.

    If `objects` is `None` the selected objects will be used instead.
    """
    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    for obj in objects:
        rotate_order_attr = utils.find_connected_source_attribute(obj['rotateOrder'])
        rotate_order_settable = mx.cmd.getAttr(rotate_order_attr, settable=True)

        if rotate_order_settable and (is_ctrl(obj) or not get_space_ctrls(obj)):
            return True

    return False


def constraint_attributes(constraint_type):
    """Retrieve the animation attributes associated with a constraint type."""
    if constraint_type == ConstraintType.POSITION:
        return ['translate']

    if constraint_type == ConstraintType.ROTATION:
        return ['rotate']

    return ['translate', 'rotate']


def get_space_ctrls(obj):
    """Get the space controls for the specified object."""
    ctrls = []

    if is_ctrl(obj):
        obj = obj.target

        if not obj:
            return []

    for node in obj['message'].outputs():
        if is_ctrl(node):
            ctrls.append(node)

    return ctrls


@mx.undoable
def initiate_operation(operation, *args, **kwargs):
    """Initiate a multi-step operation."""
    if operation == OperationType.PIVOT:
        _initiate_pivot_change(*args, **kwargs)
    elif operation == OperationType.AIM:
        _initiate_aim_space(*args, **kwargs)

    set_active_operation(operation)


@mx.undoable
def apply_operation(*args, **kwargs):
    """Apply the active multi-step operation."""
    operation = get_active_operation()

    if operation == OperationType.PIVOT:
        _apply_pivot_change(*args, **kwargs)
    elif operation == OperationType.AIM:
        _apply_aim_space(*args, **kwargs)

    delete_temp_grp()
    set_active_operation(OperationType.NONE)


@mx.undoable
def cancel_operation():
    """Cancel the active multi-step operation."""
    delete_temp_grp()
    set_active_operation(OperationType.NONE)


@mx.undoable
def _initiate_pivot_change(objects, ctrl_type, ctrl_color):
    """Create the temporary controls for changing the objects' pivot.

    If `objects` is `None` the selected objects will be used instead.
    """
    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    temp_ctrls = []

    for obj in objects:
        ctrl = create_temp_ctrl(
            '{}_{}'.format(obj.name, CTRL_SUFFIX_PIVOT),
            ctrl_type,
            ctrl_color,
            target=obj,
        )

        temp_ctrls.append(ctrl)

    mx.cmd.select(temp_ctrls)

    utils.enable_move_tool()


@utils.time_logger
@mx.undoable
def _apply_pivot_change(bake_non_keyed=True, bake_options=None):
    """Change the objects' pivot."""
    temp_ctrls = all_temp_ctrls()

    if temp_ctrls:
        anim_to_world(
            temp_ctrls,
            constraint_type=ConstraintType.PARENT,
            bake_non_keyed=bake_non_keyed,
            bake_options=bake_options,
        )


@mx.undoable
def _initiate_aim_space(objects, ctrl_type, ctrl_color):
    """Create the temporary controls for changing the objects' aim space.

    If `objects` is `None` the selected objects will be used instead.
    """
    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    temp_ctrls = []
    ctrls_to_select = []

    for obj in objects:
        obj_radius = utils.get_bbox_average_radius(obj)

        origin_ctrl = create_ctrl(
            obj.name + '_aimAxes',
            CtrlType.SPHERE,
            COLOR_YELLOW,
            parent=get_temp_grp(),
            with_buffer=True,
        )

        forward_ctrl = create_temp_ctrl(
            '{}_{}'.format(obj.name, CTRL_SUFFIX_AIM_FORWARD),
            ctrl_type,
            ctrl_color,
            target=obj,
            with_buffer=True,
        )
        up_ctrl = create_temp_ctrl(
            '{}_{}'.format(obj.name, CTRL_SUFFIX_AIM_UP),
            ctrl_type,
            ctrl_color,
            target=obj,
            with_buffer=True,
        )

        origin_ctrl.worldScale = [obj_radius * 1.5] * 3

        forward_ctrl.translate = (0, 0, obj_radius * 5)
        forward_ctrl.rotateX = 90
        up_ctrl.translate = (0, obj_radius * 5, 0)

        forward_ctrl['translateX'].locked = True
        forward_ctrl['translateY'].locked = True
        up_ctrl['translateX'].locked = True
        up_ctrl['translateZ'].locked = True

        mx.cmd.parentConstraint(obj, origin_ctrl.buffer)
        mx.cmd.parentConstraint(origin_ctrl, forward_ctrl.buffer, maintainOffset=True)
        mx.cmd.parentConstraint(origin_ctrl, up_ctrl.buffer, maintainOffset=True)

        utils.lock_transform_attributes(origin_ctrl.buffer)
        utils.lock_transform_attributes(origin_ctrl, rotation=False)
        utils.lock_transform_attributes(forward_ctrl.buffer)
        utils.lock_transform_attributes(up_ctrl.buffer)

        forward_connection = utils.create_connection_guide(forward_ctrl, obj)
        up_connection = utils.create_connection_guide(up_ctrl, obj)

        origin_ctrl.lineWidth = 5
        forward_connection.lineWidth = 5
        up_connection.lineWidth = 5

        utils.override_object_color(forward_connection, COLOR_YELLOW)
        utils.override_object_color(up_connection, COLOR_TAN)

        temp_ctrls.append(forward_ctrl)
        temp_ctrls.append(up_ctrl)
        ctrls_to_select.append(origin_ctrl)

    mx.cmd.select(ctrls_to_select)

    utils.enable_rotate_tool()


@utils.time_logger
@mx.undoable
def _apply_aim_space(bake_non_keyed=True, bake_options=None):
    """Change the objects' aim space."""
    baked_attrs = constraint_attributes(ConstraintType.PARENT)

    targets_without_keys = []
    baked_ctrls = []
    baked_targets = []
    temp_objects = []

    aim_ctrls = [ctrl for ctrl in all_temp_ctrls() if ctrl.target]
    aim_ctrls.sort(
        key=lambda ctrl: (ctrl.target.name, not ctrl.name.endswith(CTRL_SUFFIX_AIM_FORWARD))
    )

    if not aim_ctrls:
        return

    for ctrl in aim_ctrls:
        ctrl['translateX'].locked = False
        ctrl['translateY'].locked = False
        ctrl['translateZ'].locked = False

        make_temp_ctrl_permanent(ctrl, ignore_buffer=True)

        connection_line = ctrl.shapes[1]
        connection_line.lineWidth = -1
        connection_line.template = True

    delete_temp_grp()

    for i in range(0, len(aim_ctrls), 2):
        forward_ctrl = aim_ctrls[i]
        up_ctrl = aim_ctrls[i + 1]
        target = forward_ctrl.target

        forward_constraint = mx.cmd.parentConstraint(target, forward_ctrl, maintainOffset=True)[0]
        up_constraint = mx.cmd.parentConstraint(target, up_ctrl, maintainOffset=True)[0]

        if utils.has_keys(target, baked_attrs):
            target_has_keys = True
        else:
            target_has_keys = False
            targets_without_keys.append(target)

        if target_has_keys or bake_non_keyed:
            baked_ctrls.append(forward_ctrl)
            baked_ctrls.append(up_ctrl)

            baked_targets.append(target)

        temp_objects.append(forward_constraint)
        temp_objects.append(up_constraint)

    if baked_ctrls:
        if targets_without_keys and bake_non_keyed:
            baked_time = utils.get_time_range()
        else:
            frames_with_keys = utils.get_frames_with_keys(baked_targets, baked_attrs)
            baked_time = (frames_with_keys[0], frames_with_keys[-1])

        do_smart_baking(
            baked_ctrls,
            source_objects=baked_targets,
            time_range=baked_time,
            attributes=baked_attrs,
            bake_options=bake_options,
        )

    mx.cmd.delete(temp_objects)

    for i in range(0, len(aim_ctrls), 2):
        forward_ctrl = aim_ctrls[i]
        up_ctrl = aim_ctrls[i + 1]
        target = forward_ctrl.target

        mx.cmd.aimConstraint(
            forward_ctrl,
            target,
            worldUpType='object',
            worldUpObject=up_ctrl,
            skip=utils.get_locked_rotate_axes(target),
            maintainOffset=True,
        )

        utils.lock_rotation_attributes(forward_ctrl)
        utils.lock_rotation_attributes(up_ctrl)

    mx.cmd.select(aim_ctrls)


@mx.undoable
def do_smart_baking(
    objects,
    source_objects=None,
    time_range=None,
    attributes=(),
    bake_options=None,
):
    """Bake objects and remove unnecessary keys."""
    time_range = time_range or utils.get_time_range()
    bake_options = bake_options or {}

    if 'preserve_keys' in bake_options:
        preserve_keys = bake_options['preserve_keys']
        bake_options = {
            name: value for name, value in bake_options.items() if name != 'preserve_keys'
        }

    if not bake_options['smart']:
        time_range = (round(time_range[0]), round(time_range[1]))

    bake(objects, time_range, attributes, **bake_options)

    if not source_objects:
        return

    if len(source_objects) > len(objects):
        if len(source_objects) % len(objects):
            raise AnimLocatorError('Wrong number of source objects.')

        diff = int(len(source_objects) / len(objects))
        source_objects = [
            tuple(source_objects[i : i + diff]) for i in range(0, len(source_objects), diff)
        ]
    elif len(source_objects) < len(objects):
        if len(objects) % len(source_objects):
            raise AnimLocatorError('Wrong number of source objects.')

        diff = int(len(objects) / len(source_objects))
        source_objects = [obj for obj in source_objects for _ in range(diff)]

    for i, obj in enumerate(objects):
        source_obj = source_objects[i]

        if isinstance(source_obj, tuple):
            source_frames_with_keys = utils.get_frames_with_keys(source_obj, attributes)
        else:
            source_frames_with_keys = utils.get_frames_with_keys([source_obj], attributes)

        if not source_frames_with_keys:
            continue

        if not bake_options['smart']:
            mx.cmd.cutKey(
                obj,
                time=(time_range[0] - 1, source_frames_with_keys[0] - 1),
                clear=True,
            )
            mx.cmd.cutKey(
                obj,
                time=(source_frames_with_keys[-1] + 1, time_range[1] + 1),
                clear=True,
            )

        if preserve_keys:
            baked_frames = utils.get_frames_with_keys([obj], attributes)
            keys_to_remove = list(set(baked_frames).difference(source_frames_with_keys))

            if keys_to_remove:
                mx.cmd.cutKey(obj, time=[(frame,) for frame in keys_to_remove], clear=True)


@mx.undoable
def bake(
    objects,
    time_range=None,
    attributes=(),
    smart=DEFAULT_BAKE_OPTION_SMART,
    simulate=DEFAULT_BAKE_OPTION_SIMULATE,
    use_dg=DEFAULT_BAKE_OPTION_DG,
    remove_from_layers=False,
):
    """Run a bake operation on the passed objects."""
    if not time_range:
        time_range = utils.get_time_range()

    mx.cmd.refresh(suspend=True)

    if use_dg:
        evaluation_mode = mx.cmd.evaluationManager(query=True, mode=True)[0]

        if evaluation_mode != 'off':
            mx.cmd.evaluationManager(mode='off')

    try:
        if time_range[0] == time_range[1]:
            current_time = mx.cmd.currentTime(query=True)

            mx.cmd.currentTime(time_range[0])
            mx.cmd.setKeyframe(objects, attribute=attributes)
            mx.cmd.currentTime(current_time)
        else:
            try:
                mx.cmd.bakeResults(
                    objects,
                    time=time_range,
                    smart=(smart,),
                    simulation=simulate,
                    attribute=attributes,
                    sampleBy=1,
                    oversamplingRate=1,
                    disableImplicitControl=True,
                    preserveOutsideKeys=True,
                    minimizeRotation=True,
                    bakeOnOverrideLayer=False,
                    removeBakedAnimFromLayer=False,
                    removeBakedAttributeFromLayer=False,
                )
            except RuntimeError as error:
                raise AnimLocatorBakeError('Baking failed because of "{}"'.format(error))

            if remove_from_layers:
                for obj in objects:
                    utils.remove_from_anim_layers(obj)

        mx.cmd.filterCurve(objects, filter='euler')
    finally:
        if use_dg and evaluation_mode != 'off':
            mx.cmd.evaluationManager(mode=evaluation_mode)

        mx.cmd.refresh(suspend=False)
