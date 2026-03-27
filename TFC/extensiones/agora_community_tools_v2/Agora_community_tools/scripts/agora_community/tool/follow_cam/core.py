"""The core functionality for the Follow Cam tool."""

from maya import cmds

from agora_community.vendor import mayax as mx
from agora_community.mayalib import get_tool_group

from .constants import *


class FollowCamError(Exception):
    """Base class for all custom exceptions."""


@mx.undoable
def create_follow_camera(objects=None, translate_only=True, ignore_up_axis=False):
    """Create the follow camera.

    If `objects` is `None` the selected objects will be used instead.
    """
    if objects is None:
        objects = mx.cmd.ls(selection=True, transforms=True)

    if not objects:
        raise FollowCamError('No objects selected.')

    current_camera = mx.cmd.lookThru(query=True)

    if not current_camera:
        raise FollowCamError('No active camera found.')

    if current_camera.type != 'transform':
        current_camera = current_camera.parent

    if len(objects) > 1:
        objects_name = '{}_{}'.format(objects[0].name, objects[-1].name)
    else:
        objects_name = objects[0].name

    instance_grp = mx.cmd.createNode(
        'transform',
        name='followGrp_' + objects_name,
        parent=get_root_grp(),
        skipSelect=True,
    )
    instance_grp.addAttr('source_camera', current_camera)

    if translate_only:
        mx.cmd.pointConstraint(
            objects,
            instance_grp,
            skip=cmds.upAxis(query=True, axis=True) if ignore_up_axis else [],
        )
    else:
        mx.cmd.parentConstraint(objects, instance_grp)

    follow_camera = mx.cmd.camera(name='followCam_' + objects_name)[0]
    follow_camera.parent = instance_grp
    follow_camera.worldMatrix = current_camera.worldMatrix
    follow_camera.centerOfInterest = current_camera.centerOfInterest

    mx.cmd.lookThru(follow_camera)
    mx.cmd.select(objects)

    cmds.inViewMessage(
        message='<font color="yellow">Looking through: {}</font>'.format(follow_camera),
        position='midCenter',
        fontSize=24,
        fade=True,
        fadeStayTime=1000,
    )


@mx.undoable
def delete_all_follow_cameras():
    """Remove all follow cameras."""
    instances = get_follow_instances()

    if not instances:
        return

    previous_camera = None

    for instance_grp in instances:
        previous_camera = instance_grp.source_camera
        instance_grp.delete()

    if previous_camera:
        mx.cmd.lookThru(previous_camera)
    else:
        mx.cmd.lookThru('persp')


@mx.undoable
def get_root_grp(query_only=False):
    """Retrieve the root group.

    If it doesn't exist, it will be created (unless `query_only` is `True`).
    """
    root_grp = get_tool_group(TOOL_NAME, query_only=query_only)

    if root_grp:
        return mx.Node(root_grp)

    return None


def get_follow_instances():
    """Retrieve the follow instances."""
    root_grp = get_root_grp(query_only=True)

    if root_grp:
        return root_grp.children

    return []
