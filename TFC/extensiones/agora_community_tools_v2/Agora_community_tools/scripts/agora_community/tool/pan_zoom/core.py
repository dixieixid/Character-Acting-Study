"""The core functionality for the Pan Zoom tool."""

import math

from agora_community.vendor import mayax as mx
from agora_community.mayalib import get_tool_group

from . import utils
from .constants import *


class PanZoomError(Exception):
    """Base class for all custom exceptions."""


@mx.undoable
def track_objects(objects=None, camera=None, zoom=1.0):
    """Adjust the camera's 2D Pan/Zoom to keep the objects in frame.

    If `objects` is `None` the selected objects will be used instead.
    If `camera` is `None` the last one found will be used.
    """
    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    if not objects:
        raise PanZoomError('No objects provided.')

    if camera is None:
        camera = utils.get_active_camera()

    if camera.type != 'transform':
        camera = camera.parent

    # Frame the objects first to hide the camera update delay with slow rigs.
    frame_objects(objects, camera, zoom)
    mx.cmd.refresh()

    fov = math.radians(mx.cmd.camera(camera, query=True, horizontalFieldOfView=True))
    view_distance = (camera.horizontalFilmAperture * 0.5) / math.tan(fov * 0.5)

    instance_grp = mx.cmd.createNode(
        'dagContainer',
        name='track_' + camera.name,
        parent=get_root_grp(),
        skipSelect=True,
    )

    view_center_node = mx.cmd.createNode(
        'transform',
        name='view_center',
        parent=instance_grp,
        skipSelect=True,
    )
    view_center_node.translateZ = -view_distance
    camera['worldMatrix'].connect(view_center_node['offsetParentMatrix'])

    target_node = mx.cmd.createNode('transform', skipSelect=True)
    camera['worldMatrix'].connect(target_node['offsetParentMatrix'])
    mx.cmd.pointConstraint(objects, target_node)

    # Set target parent after constraints because of issue with it and dagContainer.
    target_node.parent = instance_grp
    target_node.name = 'target'

    angle_node = utils.create_angle_between_node(
        view_center_node['translate'],
        target_node['translate'],
        'target_angle',
    )

    cos_node, cos_extra_node = utils.create_cos_node(angle_node['angle'], 'target_cos')

    target_distance_node = mx.cmd.createNode(
        'multiplyDivide',
        name='target_distance',
        skipSelect=True,
    )
    target_distance_node.operation = 2  # divide
    target_distance_node.input1X = view_distance
    cos_node['outputQuatW'].connect(target_distance_node['input2X'])

    target_view_direction_node, target_view_extra_node = utils.create_scaled_vector_node(
        target_node['translate'],
        target_distance_node['outputX'],
        'target_view_direction',
    )

    target_local_mtx_node = mx.cmd.createNode(
        'composeMatrix',
        name='target_localMtx',
        skipSelect=True,
    )
    target_view_direction_node['output'].connect(target_local_mtx_node['inputTranslate'])

    target_world_mtx_node = mx.cmd.createNode('multMatrix', name='target_mtx', skipSelect=True)
    target_local_mtx_node['outputMatrix'].connect(target_world_mtx_node['matrixIn[0]'])
    camera['worldMatrix'].connect(target_world_mtx_node['matrixIn[1]'])

    target_relative_mtx_node = mx.cmd.createNode(
        'multMatrix',
        name='target_relativeMtx',
        skipSelect=True,
    )
    target_world_mtx_node['matrixSum'].connect(target_relative_mtx_node['matrixIn[0]'])
    view_center_node['worldInverseMatrix'].connect(target_relative_mtx_node['matrixIn[1]'])

    target_pan_mtx_node = mx.cmd.createNode(
        'decomposeMatrix',
        name='target_panMtx',
        skipSelect=True,
    )
    target_relative_mtx_node['matrixSum'].connect(target_pan_mtx_node['inputMatrix'])

    target_pan_mtx_node['outputTranslateX'].connect(camera['horizontalPan'])
    target_pan_mtx_node['outputTranslateY'].connect(camera['verticalPan'])

    camera.panZoomEnabled = True
    camera.zoom = zoom

    mx.cmd.container(
        instance_grp,
        edit=True,
        addNode=[
            view_center_node,
            target_node,
            angle_node,
            cos_node,
            cos_extra_node,
            target_distance_node,
            target_view_direction_node,
            target_view_extra_node,
            target_local_mtx_node,
            target_world_mtx_node,
            target_relative_mtx_node,
            target_pan_mtx_node,
        ],
    )

    instance_grp.addAttr('camera', camera)
    instance_grp.addAttr('target', target_node)

    mx.cmd.select(objects)


@mx.undoable
def untrack():
    """Disable tracking."""
    tracked_instances = get_tracked_instances()

    for instance_grp in tracked_instances:
        camera = instance_grp.camera

        if camera:
            camera['horizontalPan'].disconnectInput()
            camera['verticalPan'].disconnectInput()

            camera.panZoomEnabled = False
            camera.horizontalPan = 0
            camera.verticalPan = 0
            camera.zoom = 1

            # Refresh to hide the camera update delay with slow rigs.
            mx.cmd.refresh()

        for node in mx.cmd.container(instance_grp, query=True, nodeList=True):
            if node.type == 'vectorProduct':
                # delete the vectorProduct nodes first to avoid "zero-length output vector" error
                node.delete()

        mx.cmd.delete(instance_grp)


@mx.undoable
def frame_objects(objects=None, camera=None, zoom=1.0):
    """Adjust the camera's 2D Pan/Zoom to put the objects in frame.

    If `objects` is `None` the selected objects will be used instead.
    If `camera` is `None` the last one found will be used.
    """
    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    if not objects:
        raise PanZoomError('No objects provided.')

    if camera is None:
        camera = utils.get_active_camera()

    if camera.type != 'transform':
        camera = camera.parent

    camera_position = utils.get_world_position(camera)
    target_position = utils.get_objects_center(objects)

    fov = math.radians(mx.cmd.camera(camera, query=True, horizontalFieldOfView=True))
    view_direction = utils.get_camera_view_direction(camera)
    view_distance = (camera.horizontalFilmAperture * 0.5) / math.tan(fov * 0.5)
    view_center = camera_position + view_direction * view_distance

    target_direction = (target_position - camera_position).normal()
    target_angle = view_direction.angle(target_direction)
    target_distance = view_distance / math.cos(target_angle)
    target_view_position = camera_position + target_direction * target_distance

    view_center_mtx = camera.worldMatrix
    utils.set_matrix_position(view_center_mtx, view_center)

    target_view_mtx = mx.Matrix()
    utils.set_matrix_position(target_view_mtx, target_view_position)

    pan_coords = utils.get_matrix_position(target_view_mtx * view_center_mtx.inverse())

    camera.panZoomEnabled = True
    camera.horizontalPan = pan_coords.x
    camera.verticalPan = pan_coords.y
    camera.zoom = zoom


def update_zoom(zoom_value, camera=None):
    """Update the camera's 2D zoom."""
    if camera is None:
        camera = utils.get_active_camera()

    if camera.type != 'transform':
        camera = camera.parent

    camera.panZoomEnabled = True
    camera.zoom = zoom_value


@mx.undoable
def get_root_grp(query_only=False):
    """Retrieve the root group.

    If it doesn't exist, it will be created (unless `query_only` is `True`).
    """
    root_grp = get_tool_group(TOOL_NAME, query_only=query_only)

    if root_grp:
        return mx.Node(root_grp)

    return None


def get_tracked_instances():
    """Retrieve the tracked instances."""
    root_grp = get_root_grp(query_only=True)

    if root_grp:
        return root_grp.children

    return []


def get_tracked_camera():
    """Retrieve the tracked camera."""
    try:
        return get_tracked_instances()[0].camera
    except IndexError:
        return None


def get_tracked_objects():
    """Retrieve the tracked objects."""
    try:
        instance_grp = get_tracked_instances()[0]
    except IndexError:
        return []

    return mx.cmd.pointConstraint(instance_grp.target, query=True, targetList=True)


def is_tracking_enabled():
    """Check if tracking is enabled."""
    return bool(get_tracked_instances())


def is_panzoom_enabled():
    """Check if 2D Pan/Zoom is enabled."""
    try:
        camera = get_tracked_instances()[0].camera
    except IndexError:
        camera = utils.get_active_camera()

    return camera.panZoomEnabled


def toggle_panzoom():
    """Enable/disable the 2D Pan/Zoom."""
    try:
        camera = get_tracked_instances()[0].camera
    except IndexError:
        camera = utils.get_active_camera()

    camera.panZoomEnabled = not camera.panZoomEnabled
