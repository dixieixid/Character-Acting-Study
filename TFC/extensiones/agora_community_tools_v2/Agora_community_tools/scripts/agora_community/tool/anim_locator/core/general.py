"""General functionality."""

from agora_community.vendor import mayax as mx
from agora_community.mayalib import get_tool_group

from ..constants import *
from .types import OperationType
from . import utils


@mx.undoable
def get_root_grp(query_only=False):
    """Retrieve the root group.

    If it doesn't exist, it will be created (unless `query_only` is `True`).
    """
    try:
        return mx.Node(get_tool_group(TOOL_NAME, path_only=True))
    except mx.MayaNodeError:
        if query_only:
            return None

        root = mx.Node(get_tool_group(TOOL_NAME))
        root.addAttr('active_operation', OperationType.NONE)

        return root


@mx.undoable
def get_temp_grp(query_only=False):
    """Retrieve the temporary group.

    If it doesn't exist, it will be created (unless `query_only` is `True`).
    """
    try:
        return mx.Node(
            '{}|{}'.format(
                get_tool_group(TOOL_NAME, path_only=True),
                TEMP_GRP_NAME,
            )
        )
    except mx.MayaNodeError:
        if query_only:
            return None

        temp_grp = mx.cmd.createNode(
            'transform',
            name=TEMP_GRP_NAME,
            parent=get_root_grp(),
            skipSelect=True,
        )

        mx.cmd.reorder(temp_grp, front=True)

        utils.lock_transform_attributes(temp_grp)
        mx.cmd.setAttr(temp_grp['visibility'], lock=True, keyable=False, channelBox=False)

        return temp_grp


@mx.undoable
def delete_temp_grp():
    """Remove the temporary group."""
    temp_grp = get_temp_grp(query_only=True)

    if temp_grp:
        temp_grp.delete()


def get_active_operation():
    """Retrieve the active multi-step operation."""
    root_grp = get_root_grp(query_only=True)

    if not root_grp:
        return OperationType.NONE

    return root_grp.active_operation


@mx.undoable
def set_active_operation(operation):
    """Change the active multi-step operation."""
    root_grp = get_root_grp()
    root_grp.active_operation = operation
