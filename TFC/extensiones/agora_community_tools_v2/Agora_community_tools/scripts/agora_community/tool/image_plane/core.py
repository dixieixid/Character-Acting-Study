"""The core functionality for the Image Plane tool."""

import os

from maya import cmds

from agora_community.vendor import mayax as mx
from agora_community.mayalib import get_tool_group
from agora_community.mayalib.cameras import (
    is_film_gate_active,
    is_resolution_gate_active,
)
from agora_community.mayalib.image_planes import (
    fit_image_plane_to_film_gate,
    fit_image_plane_to_resolution_gate,
    is_image_sequence,
)

from . import utils
from .constants import *


_IMAGE_PLANE_ATTR_MAP = {
    'opacity': 'alphaGain',
    'visible_in_all_views': 'displayOnlyIfCurrent',
}


class ImagePlaneError(Exception):
    """Base class for all custom exceptions."""


class ImagePlaneGate:
    Resolution = 'resolution_gate'
    Film = 'film_gate'


@mx.undoable
def add_image_plane(file_path):
    """Add an image plane to active camera."""
    camera = utils.get_active_camera()
    if not camera:
        raise ImagePlaneError('No active camera found.')

    name = os.path.splitext(os.path.basename(file_path))[0]
    image_plane = mx.cmd.imagePlane(
        name=name,
        camera=camera,
        maintainRatio=True,
        showInAllViews=False,
    )[0]

    if utils.is_video_file(file_path):
        image_plane['type'].value = 2
    else:
        image_plane['type'].value = 0

    image_plane.imageName = file_path
    image_plane.useFrameExtension = is_image_sequence(file_path)

    update_image_plane_property(image_plane, 'frame_start', int(utils.get_playback_range()[0]))

    # If film or resolution gates are enabled, fit to them.
    if is_film_gate_active(camera.name):
        fit_image_plane_to_film_gate(image_plane.name)
    elif is_resolution_gate_active(camera.name):
        fit_image_plane_to_resolution_gate(image_plane.name)


@mx.undoable
def update_image_plane_property(node, attr_name, attr_value):
    """Update property of an image plane."""
    if attr_name == 'frame_start':
        frame_start, frame_offset = get_image_plane_frame_info(node)
        frame_start = attr_value
        if node.hasAttr('frame_start'):
            node.frame_start = frame_start
        else:
            node.addAttr('frame_start', frame_start)

        node.frameOffset = (frame_start + frame_offset - 1) * -1
        return

    if attr_name == 'frame_offset':
        frame_start, frame_offset = get_image_plane_frame_info(node)
        frame_offset = attr_value

        if not node.hasAttr('frame_start'):
            node.addAttr('frame_start', frame_start)

        node.frameOffset = (frame_start + frame_offset - 1) * -1
        return

    if attr_name == 'camera_name':
        camera = mx.Node(attr_value) if attr_value else None
        change_image_plane_camera(node, camera)
        return

    if attr_name == 'selectable':
        node_shape = node.shapes[0]
        if attr_value:
            node_shape.overrideDisplayType = 0
        else:
            node_shape.overrideEnabled = True
            node_shape.overrideDisplayType = 2
        return

    if attr_name == 'fit_to_resolution_gate':
        fit_image_plane(node, ImagePlaneGate.Resolution)
        return

    if attr_name == 'fit_to_film_gate':
        fit_image_plane(node, ImagePlaneGate.Film)
        return

    if attr_name == 'time_remap':
        remap_image_plane_time(node, attr_value)
        return

    if attr_name == 'visible_in_all_views':
        attr_value = not attr_value

    if attr_name in _IMAGE_PLANE_ATTR_MAP:
        attr_name = _IMAGE_PLANE_ATTR_MAP[attr_name]

    node[attr_name].value = attr_value


@mx.undoable
def change_image_plane_camera(node, camera):
    """Change the camera for the image plane."""
    current_camera = utils.get_image_plane_camera(node)

    if camera:
        mx.cmd.imagePlane(node, edit=True, camera=camera)

        if not current_camera:
            node.displayOnlyIfCurrent = True
    else:
        mx.cmd.imagePlane(node, edit=True, detach=True)

        node.parent = get_root_grp()
        node.displayOnlyIfCurrent = False

        if current_camera:
            mx.cmd.matchTransform(node, current_camera, position=True, rotation=True)
            mx.cmd.move(-25, node, z=True, objectSpace=True, relative=True)

        node.width = node.coverageX / 100.0
        node.height = node.coverageY / 100.0


def fit_image_plane(node, gate):
    """Fit an image plane to its camera by gate type."""
    if gate == ImagePlaneGate.Film:
        fit_image_plane_to_film_gate(node.name)
    elif gate == ImagePlaneGate.Resolution:
        fit_image_plane_to_resolution_gate(node.name)
    else:
        raise ValueError('Unsupported image plane gate type :: {}.'.format(gate))


def remap_image_plane_time(node, enabled):
    """Update the image number using animation curve."""
    if not node.hasAttr('frame_input'):
        node.addAttr('frame_input', type=mx.Node)

    if not node.hasAttr('frame_curve'):
        node.addAttr('frame_curve', type=mx.Node)

    frame_input = node['frameExtension'].input()

    if enabled:
        if frame_input and frame_input.type.startswith('animCurve'):
            return

        node.frame_input = frame_input
        node['frameExtension'].disconnectInput()

        if node.frame_curve:
            node.frame_curve['output'].connect(node['frameExtension'], force=True)
        else:
            anim_range = utils.get_animation_range()

            mx.cmd.setKeyframe(
                node['frameExtension'],
                time=anim_range[0],
                value=anim_range[0],
                inTangentType='linear',
                outTangentType='linear',
            )
            mx.cmd.setKeyframe(
                node['frameExtension'],
                time=anim_range[1],
                value=anim_range[1],
                inTangentType='linear',
                outTangentType='linear',
            )

            node.frame_curve = node['frameExtension'].input()
    else:
        if not frame_input or not frame_input.type.startswith('animCurve'):
            return

        if node.frame_input:
            node.frame_input['output'].connect(node['frameExtension'], force=True)
        else:
            mx.Node('time1')['outTime'].connect(node['frameExtension'], force=True)


@mx.undoable
def select_image_plane(node):
    """Select the image plane."""
    node.select()


@mx.undoable
def select_image_plane_camera(node):
    """Select the camera for the image plane."""
    camera = utils.get_image_plane_camera(node)
    if camera:
        camera.select()


@mx.undoable
def select_image_plane_frame_curve(node):
    """Select the animation curve for frame number."""
    if node.hasAttr('frame_curve') and node.frame_curve:
        node.frame_curve.select()
        cmds.GraphEditor()


@mx.undoable
def delete_image_plane(node):
    """Delete the image plane."""
    node.delete()


@mx.undoable
def hide_image_plane(node=None):
    """Hide the image plane."""
    for node in [node] if node else mx.cmd.ls(type='imagePlane'):
        node.displayMode = 0  # None
        node.useFrameExtension = False


@mx.undoable
def show_image_plane(node=None):
    """Show the image plane."""
    for node in [node] if node else mx.cmd.ls(type='imagePlane'):
        node.displayMode = 3  # RGBA
        node.useFrameExtension = True


def get_image_plane_frame_info(node):
    """Retrieve the image plane's frame start and offset."""
    if node.hasAttr('frame_start'):
        frame_start = node.frame_start
        frame_offset = (node.frameOffset * -1 + 1) - node.frame_start
    else:
        frame_start = node.frameOffset * -1 + 1
        frame_offset = 0

    return frame_start, frame_offset


def get_image_planes_info():
    """Retrieve all the image planes available."""
    info = []

    for node_shape in mx.cmd.ls(type='imagePlane'):
        node = node_shape.parent
        camera = utils.get_image_plane_camera(node)

        frame_input = node['frameExtension'].input()
        time_remap = bool(frame_input and frame_input.type.startswith('animCurve'))

        frame_start, frame_offset = get_image_plane_frame_info(node)

        info.append(
            {
                'node': node,
                'camera_name': camera.uniqueName if camera else '',
                'frame_start': frame_start,
                'frame_offset': frame_offset,
                'depth': node_shape.depth,
                'opacity': node_shape.alphaGain,
                'visible': bool(node.displayMode),
                'visible_in_all_views': not node_shape.displayOnlyIfCurrent,
                'selectable': not node_shape.overrideEnabled or node_shape.overrideDisplayType == 0,
                'time_remap': time_remap,
            }
        )

    return info


@mx.undoable
def get_root_grp(query_only=False):
    """Retrieve the root group.

    If it doesn't exist, it will be created (unless `query_only` is `True`).
    """
    root_grp = get_tool_group(TOOL_NAME, query_only=query_only)
    if root_grp:
        return mx.Node(root_grp)

    return None
