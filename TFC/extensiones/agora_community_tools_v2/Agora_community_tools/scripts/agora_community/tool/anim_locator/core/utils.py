"""Utility functions."""

import functools

from maya import cmds, mel

from agora_community.vendor import mayax as mx

from ..constants import *


def index_colors():
    """Retrieve the available index colors."""
    colors = list(range(1, 31))
    colors.sort(key=lambda color: mx.cmd.colorIndex(color, query=True, hueSaturationValue=True)[0])
    colors.reverse()

    return colors


def color_index_to_rgb(color_index):
    """Retrieve the RGB values of a color index."""
    return [int(value * 255) for value in mx.cmd.colorIndex(color_index, query=True)]


@mx.undoable
def override_object_color(obj, color_index, first_shape_only=False):
    """Override the color of an object.

    Pass `0` for `color_index` to revert back to default color.
    """
    all_nodes = [obj]
    obj_shapes = obj.shapes

    if first_shape_only and obj_shapes:
        all_nodes.append(obj_shapes[0])
    else:
        all_nodes += obj_shapes

    for node in all_nodes:
        if color_index:
            node.overrideEnabled = True
            node.overrideColor = color_index
        else:
            node.overrideEnabled = False


@mx.undoable
def lock_transform_attributes(obj, position=True, rotation=True, scale=True):
    """Lock and hide the transform attributes."""
    attrs = []

    if position:
        attrs.extend(['translateX', 'translateY', 'translateZ'])

    if rotation:
        attrs.extend(['rotateX', 'rotateY', 'rotateZ'])

    if scale:
        attrs.extend(['scaleX', 'scaleY', 'scaleZ'])

    for attr_name in attrs:
        mx.cmd.setAttr(obj[attr_name], lock=True, keyable=False, channelBox=False)


@mx.undoable
def lock_position_attributes(obj):
    """Lock and hide the position attributes."""
    lock_transform_attributes(obj, rotation=False, scale=False)


@mx.undoable
def lock_rotation_attributes(obj):
    """Lock and hide the rotation attributes."""
    lock_transform_attributes(obj, position=False, scale=False)


@mx.undoable
def lock_scale_attributes(obj):
    """Lock and hide the scale attributes."""
    lock_transform_attributes(obj, position=False, rotation=False)


@mx.undoable
def create_connection_guide(origin_object, target_object):
    """Create a line between two objects.

    The line shape will be added to the `origin_object`.
    """
    curve = mx.cmd.curve(degree=1, point=[(0, 0, 0), (0, 0, 0)])
    curve_shape = curve.shapes[0]

    mx.cmd.parent(curve_shape, origin_object, shape=True, relative=True)

    curve.delete()
    curve_shape.name = origin_object.name + 'GuideShape'

    multiply_mtx_node = mx.cmd.createNode(
        'multMatrix',
        name=origin_object.name + '_guideMtx1',
        skipSelect=True,
    )
    decomposed_mtx_node = mx.cmd.createNode(
        'decomposeMatrix',
        name=origin_object.name + '_guideMtx2',
        skipSelect=True,
    )

    target_object['worldMatrix'].connect(multiply_mtx_node['matrixIn[0]'])
    curve_shape['parentInverseMatrix'].connect(multiply_mtx_node['matrixIn[1]'])

    multiply_mtx_node['matrixSum'].connect(decomposed_mtx_node['inputMatrix'])
    decomposed_mtx_node['outputTranslate'].connect(curve_shape['controlPoints[1]'])

    return curve_shape


def get_bbox_average_radius(obj):
    """Retrive the bounding box average radius for the passed object."""
    if obj.type == 'joint':
        return obj.radius

    bbox = mx.cmd.exactWorldBoundingBox(obj, ignoreInvisible=True)

    min_x = min(bbox[0], bbox[3])
    min_y = min(bbox[1], bbox[4])
    min_z = min(bbox[2], bbox[5])

    max_x = max(bbox[0], bbox[3])
    max_y = max(bbox[1], bbox[4])
    max_z = max(bbox[2], bbox[5])

    len_x = max_x - min_x
    len_y = max_y - min_y
    len_z = max_z - min_z

    average_len = (len_x + len_y + len_z) / 3
    average_rad = average_len / 2

    return average_rad


def get_locked_translate_axes(obj):
    """Retrieve the locked axes for translate attribute."""
    return [axis for axis in ['x', 'y', 'z'] if obj['t' + axis].locked]


def get_locked_rotate_axes(obj):
    """Retrieve the locked axes for rotate attribute."""
    return [axis for axis in ['x', 'y', 'z'] if obj['r' + axis].locked]


def get_frames_with_keys(objects, attributes=()):
    """Get all the frames that have keys for the specified attributes."""
    frames = []

    for obj in objects:
        for attr_name in attributes:
            for frame in mx.cmd.keyframe(obj[attr_name], query=True) or []:
                if frame not in frames:
                    frames.append(frame)

    frames.sort()

    return frames


def get_time_range():
    """Retrieve the animation's time range."""
    return (
        mx.cmd.playbackOptions(query=True, animationStartTime=True),
        mx.cmd.playbackOptions(query=True, animationEndTime=True),
    )


def get_enum_values(obj, attr_name):
    """Retrieve a list with the enum values."""
    return mx.cmd.attributeQuery(attr_name, node=obj, listEnum=True)[0].split(':')


def has_keys(obj, attributes=()):
    """Check if the object has keys."""
    return bool(mx.cmd.keyframe(obj, query=True, keyframeCount=True, attribute=attributes))


def has_constraints(obj, position=True, rotation=True):
    """Check if the object has constraints."""
    constraints = mx.cmd.listRelatives(obj, type='constraint', path=True) or []

    for constraint in constraints:
        if position and constraint.type in ('parentConstraint', 'pointConstraint'):
            return True

        if rotation and constraint.type in ('parentConstraint', 'orientConstraint'):
            return True

    return False


@mx.undoable
def delete_constraints(obj, position=True, rotation=True):
    """Delete the constraints of an object."""
    constraints = mx.cmd.listRelatives(obj, type='constraint', path=True) or []

    for constraint in constraints:
        if position and constraint.type in ('parentConstraint', 'pointConstraint'):
            constraint.delete()
        elif rotation and constraint.type in ('parentConstraint', 'orientConstraint'):
            constraint.delete()


def gimbal_info(objects):
    """Retrieve gimbal locking info for the provided objects."""
    info = []
    objects_info = []

    for obj in objects:
        all_gimbal_tolerances = [int(round(t * 100)) for t in gimbal_tolerence_all(obj)]
        lowest_gimbal_tolerance = sorted(all_gimbal_tolerances)[0]
        lowest_gimbal_tolerance_world = sorted(all_gimbal_tolerances[2:4])[0]  # ('zxy', 'xzy')
        world_space_rotation = is_world_space_rotation(obj)

        obj_info = {}

        for rotate_order, rotate_order_label in enumerate(ROTATE_ORDERS):
            gimbal_tolerance = all_gimbal_tolerances[rotate_order]

            is_recommended = (
                world_space_rotation
                and gimbal_tolerance == lowest_gimbal_tolerance_world
                and rotate_order_label.endswith('y')
            ) or (not world_space_rotation and gimbal_tolerance == lowest_gimbal_tolerance)

            is_recommended_world = (
                not world_space_rotation
                and lowest_gimbal_tolerance < lowest_gimbal_tolerance_world
                and gimbal_tolerance == lowest_gimbal_tolerance_world
                and gimbal_tolerance < 30
            )

            is_recommended_nonworld = (
                world_space_rotation
                and lowest_gimbal_tolerance < lowest_gimbal_tolerance_world
                and gimbal_tolerance == lowest_gimbal_tolerance
            )

            obj_info[rotate_order_label] = {
                'gimbal_tolerance': gimbal_tolerance,
                'recommended': is_recommended,
                'recommended_world': is_recommended_world,
                'recommended_nonworld': is_recommended_nonworld,
            }

        objects_info.append(obj_info)

    for rotate_order, rotate_order_label in enumerate(ROTATE_ORDERS):
        gimbal_tolerances = []
        recommended_count = 0
        recommended_world_count = 0
        recommended_nonworld_count = 0

        for obj in objects:
            if obj.rotateOrder != rotate_order:
                shared = False
                break
        else:
            shared = True

        for obj_info in objects_info:
            obj_order_info = obj_info[rotate_order_label]

            gimbal_tolerances.append(obj_order_info['gimbal_tolerance'])

            if obj_order_info['recommended']:
                recommended_count += 1

            if obj_order_info['recommended_world']:
                recommended_world_count += 1

            if obj_order_info['recommended_nonworld']:
                recommended_nonworld_count += 1

        info.append(
            {
                'order': rotate_order,
                'label': rotate_order_label,
                'shared': shared,
                'gimbal_tolerances': gimbal_tolerances,
                'recommended_count': recommended_count,
                'recommended_world_count': recommended_world_count,
                'recommended_nonworld_count': recommended_nonworld_count,
            }
        )

    return info


def gimbal_tolerence(obj):
    """Retrieve the gimbal tolerance for the current rotation order.

    As tolerance gets close to 1, we're getting close to gimbal.
    """
    rotate_order_axes = ROTATE_ORDERS[obj.rotateOrder]
    mid_axis_value = obj['r' + rotate_order_axes[1]].value

    tolerance = abs(((mid_axis_value + 90) % 180) - 90) / 90

    return tolerance


@mx.undoable
def gimbal_tolerence_all(obj):
    """Retrieve the gimbal tolerance for all rotation orders."""
    tolerences = []

    temp_node = mx.cmd.createNode(
        'transform',
        name='__temp_gimbal_tolerance__',
        parent=obj.parent,
        skipSelect=True,
    )
    temp_node.rotate = obj.rotate
    temp_node.rotateOrder = obj.rotateOrder

    for rotate_order in ROTATE_ORDERS:
        mx.cmd.xform(temp_node, preserve=True, rotateOrder=rotate_order)

        tolerences.append(gimbal_tolerence(temp_node))

    temp_node.delete()

    return tolerences


def find_connected_source_attribute(attribute):
    """Find the source attribute if the provided `attribute` is connected."""
    attribute_input = attribute.input(plugs=True)

    while attribute_input and attribute_input.node.type != 'animCurveTU':
        attribute = attribute_input
        attribute_input = attribute_input.input(plugs=True)

    return attribute


def is_world_space_rotation(obj):
    """Check if the rotation of an object is in world space."""
    if not obj.inheritsTransform:
        return True

    parent = obj.parent

    while parent:
        if not parent.inheritsTransform:
            return True

        for attr in ('rotateX', 'rotateZ'):
            if parent[attr].value != 0:
                return False

        parent = parent.parent

    return True


def is_attribute_value_valid(obj, attr_name, attr_value):
    """Check if a value is valid for setting it into an attribute."""
    attr_type = obj[attr_name].type

    if attr_type == 'enum':
        enum_values = get_enum_values(obj, attr_name)

        if isinstance(attr_value, str):
            try:
                enum_values.index(attr_value)
            except ValueError:
                return False
        elif attr_value < 0 or attr_value >= len(enum_values):
            return False
    elif attr_type in ('double', 'doubleLinear', 'doubleAngle', 'long'):
        if not isinstance(attr_value, (float, int)):
            return False

        if attr_type == 'long' and isinstance(attr_value, float) and not attr_value.is_integer():
            return False

        if mx.cmd.attributeQuery(attr_name, node=obj, minExists=True):
            min_value = mx.cmd.attributeQuery(attr_name, node=obj, minimum=True)[0]

            if attr_value < min_value:
                return False

        if mx.cmd.attributeQuery(attr_name, node=obj, maxExists=True):
            max_value = mx.cmd.attributeQuery(attr_name, node=obj, maximum=True)[0]

            if attr_value > max_value:
                return False
    elif attr_type == 'bool' and not isinstance(attr_value, bool):
        return False

    return True


@mx.undoable
def anim_layers(obj):
    """Retrieve the animation layers of an object."""
    selected_objects = mx.cmd.ls(selection=True)

    try:
        obj.select()

        return mx.cmd.animLayer(query=True, affectedLayers=True) or []
    finally:
        if selected_objects:
            mx.cmd.select(selected_objects)
        else:
            mx.cmd.select(clear=True)


@mx.undoable
def remove_from_anim_layers(obj, delete_empty=True):
    """Remove an object from all animation layers."""
    layers = anim_layers(obj)

    if not layers:
        return

    for attr_name in cmds.listAttr(obj.uniqueName, keyable=True):
        for layer in anim_layers(obj):
            if layer.name == 'BaseAnimation':
                continue

            if mx.cmd.animLayer(layer, query=True, lock=True):
                continue

            mx.cmd.animLayer(layer, edit=True, removeAttribute=obj[attr_name])

            if delete_empty and not mx.cmd.animLayer(layer, query=True, attribute=True):
                layer.delete()


def enable_move_tool():
    """Enable Maya's move tool."""
    mel.eval('dR_DoCmd("movePress");dR_DoCmd("moveRelease");')


def enable_rotate_tool():
    """Enable Maya's rotate tool."""
    mel.eval('dR_DoCmd("rotatePress");dR_DoCmd("rotateRelease");')


def time_logger(func):
    """Measure the execution time of the decorated functions."""

    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
        start_time = cmds.timerX()

        try:
            return func(*args, **kwargs)
        finally:
            elapsed_time = cmds.timerX(startTime=start_time)

            msg = '// {} - {}: {}s //'.format(
                LOGGER.name,
                func.__name__.replace('_', ' ').strip().title(),
                round(elapsed_time, 6),
            )

            print(msg)  # do not use LOGGER to not have it catched in listening dialogs

    return func_wrapper
