"""The core functionality for the Mirror Cam tool."""

from maya import cmds, mel

from agora_community.vendor import mayax as mx
from agora_community.mayalib import get_tool_group

from .constants import *

_TRANSFORM_ATTRS = ['tx', 'ty', 'tz', 'rx', 'ry', 'rz']

mel.eval('source channelBoxCommand;')  # necessary to make `CBdeleteConnection` work


class MirrorCamError(Exception):
    """Base class for all custom exceptions."""


@mx.undoable
def create_mirror_camera(camera=None):
    """Create a mirror camera."""
    if not camera:
        camera = mx.cmd.lookThru(query=True)

    if not camera:
        raise MirrorCamError('No active camera found.')

    if camera.type != 'transform':
        camera = camera.parent

    selection = mx.cmd.ls(selection=True)

    if camera.hasAttr('mirrored_camera'):
        if not camera.mirrored_camera:
            raise MirrorCamError('Could not find the original camera.')

        mirror_camera = camera.mirrored_camera
        camera.parent.delete()
    else:
        mirror_camera = _create_mirror_camera(camera)

    mx.cmd.lookThru(mirror_camera)

    if selection:
        mx.cmd.select(selection)
    else:
        mx.cmd.select(clear=True)

    cmds.inViewMessage(
        msg='<hl>Looking through "{}"</hl>'.format(mirror_camera),
        position='midCenter',
        fade=True,
    )


@mx.undoable
def _create_mirror_camera(camera):
    camera_name = camera.name.replace(':', '_')

    mirror_grp = mx.cmd.createNode(
        'transform',
        name='mirrorCamGrp_' + camera_name,
        parent=get_root_grp(),
        skipSelect=True,
    )
    mx.cmd.parentConstraint(camera, mirror_grp)

    mirror_camera = mx.cmd.duplicate(camera, inputConnections=True)[0]
    mirror_camera.addAttr('mirrored_camera', camera)

    for attr_name in _TRANSFORM_ATTRS:
        mx.cmd.setAttr('{}.{}'.format(mirror_camera, attr_name), lock=False, keyable=True)
        mel.eval('CBdeleteConnection "{}.{}";'.format(mirror_camera, attr_name))

    mirror_camera.parent = mirror_grp
    mirror_camera.name = 'mirrorCam_' + camera_name

    for attr_name in _TRANSFORM_ATTRS:
        mx.cmd.setAttr('{}.{}'.format(mirror_camera, attr_name), lock=True, keyable=False)

    mirror_grp.scaleX *= -1

    return mirror_camera


@mx.undoable
def get_root_grp(query_only=False):
    """Retrieve the root group.

    If it doesn't exist, it will be created (unless `query_only` is `True`).
    """
    root_grp = get_tool_group(TOOL_NAME, query_only=query_only)

    if root_grp:
        return mx.Node(root_grp)

    return None
