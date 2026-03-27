"""The core functionality for Overlap tool."""

from maya import cmds

from agora_community.vendor import mayax as mx
from agora_community.mayalib import get_tool_group

from .constants import *


class OverlapError(Exception):
    """Base class for all custom exceptions."""


@mx.undoable
def create_overlap(objects=None, frame_offset=1.0, bake_options=None):
    """Create the overlap.

    If `objects` is `None` the selected objects will be used instead.
    """
    bake_options = bake_options or {}

    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    if len(objects) < 2:
        raise OverlapError('Select two or more objects.')

    instance_grp = mx.cmd.createNode(
        'transform',
        name='{}__{}'.format(objects[0].name, objects[-1].name),
        parent=get_root_grp(),
        skipSelect=True,
    )
    instance_grp.addAttr('frame_offset', frame_offset)

    aim_objects = []
    temp_constraints = []

    for obj in objects:
        aim_grp = mx.cmd.createNode(
            'transform',
            name='aim_' + obj.name,
            parent=instance_grp,
            skipSelect=True,
        )
        aim_obj = mx.cmd.createNode(
            'transform',
            name='aim',
            parent=aim_grp,
            skipSelect=True,
        )

        aim_obj.rotateOrder = obj.rotateOrder

        aim_grp.addAttr('target_obj', obj)
        aim_grp.addAttr('aim_obj', aim_obj)

        constraint = mx.cmd.parentConstraint(obj, aim_grp, maintainOffset=False)[0]

        aim_objects.append(aim_grp)
        temp_constraints.append(constraint)

    aim_tip = mx.cmd.createNode(
        'transform',
        name='aim_tip',
        parent=instance_grp,
        skipSelect=True,
    )
    aim_tip.worldPosition = objects[-1].worldPosition + (
        objects[-1].worldPosition - objects[-2].worldPosition
    )
    aim_tip_constraint = mx.cmd.parentConstraint(objects[-1], aim_tip, maintainOffset=True)[0]

    aim_objects.append(aim_tip)
    temp_constraints.append(aim_tip_constraint)

    bake(aim_objects, time_range=get_playback_range(), **bake_options)

    mx.cmd.delete(temp_constraints)

    for i in range(len(aim_objects) - 1):
        aim_grp = aim_objects[i]
        aim_target = aim_objects[i + 1]

        mx.cmd.orientConstraint(aim_grp.aim_obj, aim_grp.target_obj, maintainOffset=False)

        aimVector, upVector, worldUpVector = calculate_aim_constraint_vectors(
            aim_grp.aim_obj,
            aim_target,
        )

        mx.cmd.aimConstraint(
            aim_target,
            aim_grp.aim_obj,
            aimVector=aimVector,
            upVector=upVector,
            worldUpType='objectrotation',
            worldUpObject=aim_target,
            worldUpVector=worldUpVector,
            maintainOffset=True,
        )

    for i, aim_grp in enumerate(aim_objects):
        if i == 0:
            continue

        keyframe_offset = i * frame_offset

        mx.cmd.keyframe(aim_grp, edit=True, relative=True, timeChange=keyframe_offset)

    return instance_grp


@mx.undoable
def update_overlap(objects=None, frame_offset=1.0):
    """Update the overlap.

    If `objects` is `None` the selected objects will be used instead.
    """
    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    for overlap_grp in get_overlaps(objects):
        previous_offset = overlap_grp.frame_offset

        if frame_offset == previous_offset:
            continue

        relative_offset = frame_offset - previous_offset

        for i, aim_grp in enumerate(overlap_grp.children):
            if i == 0:
                continue

            keyframe_offset = i * relative_offset

            mx.cmd.keyframe(aim_grp, edit=True, relative=True, timeChange=keyframe_offset)

        overlap_grp.frame_offset = frame_offset


@mx.undoable
def remove_overlap(objects=None):
    """Remove the overlap.

    If `objects` is `None` the selected objects will be used instead.
    """
    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    overlaps = get_overlaps(objects)

    if overlaps:
        mx.cmd.delete(overlaps)


@mx.undoable
def bake_overlap(objects=None, frame_offset=1.0, bake_options=None, to_anim_layer=False):
    """Bake the overlap.

    If `objects` is `None` the selected objects will be used instead.
    """
    bake_options = bake_options or {}

    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    overlaps = get_overlaps(objects)

    if not overlaps:
        overlaps.append(create_overlap(objects, frame_offset, bake_options))

    baked_overlaps = []
    baked_objects = []

    for overlap_grp in overlaps:
        baked_overlaps.append(overlap_grp)
        baked_objects.extend(
            aim_grp.target_obj for aim_grp in overlap_grp.children if aim_grp.hasAttr('target_obj')
        )

    if baked_overlaps:
        bake(
            baked_objects,
            attributes=['rotate'],
            time_range=get_playback_range(),
            to_anim_layer=to_anim_layer,
            **bake_options
        )
        mx.cmd.delete(baked_overlaps)


@mx.undoable
def get_root_grp(query_only=False):
    """Retrieve the root group.

    If it doesn't exist, it will be created (unless `query_only` is `True`).
    """
    root_grp = get_tool_group(TOOL_NAME, query_only=query_only)

    if root_grp:
        return mx.Node(root_grp)

    return None


def is_overlap_creation_available(objects=None):
    """Check if overlap creation is available.

    If `objects` is `None` the selected objects will be used instead.
    """
    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    return len(objects) > 1 and not get_overlaps(objects)


def is_overlap_removal_available(objects=None):
    """Check if overlap removal is available.

    If `objects` is `None` the selected objects will be used instead.
    """
    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    return get_overlaps(objects)


def is_overlap_baking_available(objects=None):
    """Check if overlap baking is available.

    If `objects` is `None` the selected objects will be used instead.
    """
    return is_overlap_removal_available(objects)


def get_overlaps(objects):
    """Retrieve the existing overlaps."""
    root_grp = get_root_grp(query_only=True)

    if not root_grp:
        return []

    overlaps = []

    for obj in objects:
        for output_obj in obj['message'].outputs(type='transform'):
            overlap_grp = output_obj.parent

            if overlap_grp and overlap_grp.parent == root_grp and overlap_grp not in overlaps:
                overlaps.append(overlap_grp)

    return overlaps


@mx.undoable
def bake(
    objects,
    time_range=None,
    attributes=(),
    smart=False,
    simulate=DEFAULT_BAKE_OPTION_SIMULATE,
    use_dg=DEFAULT_BAKE_OPTION_DG,
    to_anim_layer=False,
):
    """Run a bake operation on the passed objects."""
    if not time_range:
        time_range = get_animation_range()

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
                if to_anim_layer:
                    previous_layers = cmds.ls(type='animLayer')

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
                    bakeOnOverrideLayer=to_anim_layer,
                    removeBakedAnimFromLayer=False,
                    removeBakedAttributeFromLayer=False,
                )

                if to_anim_layer:
                    current_layers = cmds.ls(type='animLayer')
                    new_layers = list(set(current_layers) - set(previous_layers))

                    if 'BaseAnimation' in new_layers:
                        new_layers.remove('BaseAnimation')

                    if len(new_layers) == 1:
                        cmds.rename(new_layers[0], 'Overlap')
            except RuntimeError as error:
                raise OverlapError('Baking failed because of "{}"'.format(error))

        mx.cmd.filterCurve(objects, filter='euler')
    finally:
        if use_dg and evaluation_mode != 'off':
            mx.cmd.evaluationManager(mode=evaluation_mode)

        mx.cmd.refresh(suspend=False)


def calculate_aim_constraint_vectors(obj, target):
    """Calculate the aim constraint vectors using the target for object rotation up.

    Returns the `aimVector`, `upVector` and `worldUpVector`.
    """
    obj_world_matrix = obj.worldMatrix
    target_world_matrix = target.worldMatrix
    aim_direction = (target.worldPosition - obj.worldPosition).normal()

    world_axes = [
        mx.Vector(1, 0, 0),
        mx.Vector(0, 1, 0),
        mx.Vector(0, 0, 1),
        mx.Vector(-1, 0, 0),
        mx.Vector(0, -1, 0),
        mx.Vector(0, 0, -1),
    ]

    # Convert the objects' local axes to world space.
    obj_world_axes = [world_axis * obj_world_matrix for world_axis in world_axes]
    target_world_axes = [world_axis * target_world_matrix for world_axis in world_axes]

    # Find the aim axis by checking which one points closer to the target.
    aim_axes_ratios = [obj_axis * aim_direction for obj_axis in obj_world_axes]
    aim_axis_index = aim_axes_ratios.index(max(aim_axes_ratios))
    aim_axis = world_axes[aim_axis_index]

    # Remove aim axis from those available to properly find the up axis.
    del world_axes[aim_axis_index]
    #
    opposite_aim_axis_index = world_axes.index(aim_axis * -1)
    del world_axes[opposite_aim_axis_index]
    #
    del obj_world_axes[aim_axis_index]
    del obj_world_axes[opposite_aim_axis_index]
    del target_world_axes[aim_axis_index]
    del target_world_axes[opposite_aim_axis_index]

    # Find the up axis by checking which one matches the target's axis better.
    up_axes_ratios = [obj_axis * target_world_axes[i] for i, obj_axis in enumerate(obj_world_axes)]
    up_axis = world_axes[up_axes_ratios.index(max(up_axes_ratios))]

    world_up_axis = mx.Vector(up_axis)

    return [aim_axis, up_axis, world_up_axis]


def get_animation_range():
    """Retrieve the animation's time range."""
    return (
        mx.cmd.playbackOptions(query=True, animationStartTime=True),
        mx.cmd.playbackOptions(query=True, animationEndTime=True),
    )


def get_playback_range():
    """Retrieve the playback's time range."""
    return (
        mx.cmd.playbackOptions(query=True, minTime=True),
        mx.cmd.playbackOptions(query=True, maxTime=True),
    )
