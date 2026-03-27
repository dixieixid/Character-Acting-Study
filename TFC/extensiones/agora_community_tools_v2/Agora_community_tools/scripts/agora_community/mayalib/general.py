"""General functionality."""

import os

from maya import (
    cmds,
    OpenMaya as om_old,
)

from ..constants import *
from .decorators import undoable


@undoable
def get_main_group(query_only=False):
    """Retrieve the root group of all the tools' groups.

    If it doesn't exist, it will be created (unless `query_only` is `True`).
    """
    grp_path = f'|{TOOLS_ROOT_GRP_NAME}'

    if cmds.objExists(grp_path):
        return grp_path

    if query_only:
        return None

    cmds.createNode('transform', name=TOOLS_ROOT_GRP_NAME, skipSelect=True)
    cmds.reorder(grp_path, front=True)

    cmds.setAttr(f'{grp_path}.useOutlinerColor', True)
    cmds.setAttr(f'{grp_path}.outlinerColor', *TOOLS_ROOT_GRP_COLOR)

    _set_node_icon(grp_path, TOOLS_ROOT_GRP_ICON)

    for attr_name in ['t', 'r', 's']:
        for axis in ['x', 'y', 'z']:
            cmds.setAttr(
                f'{grp_path}.{attr_name}{axis}',
                lock=True,
                keyable=False,
                channelBox=False,
            )

    cmds.setAttr(f'{grp_path}.visibility', keyable=False, channelBox=True)

    return grp_path


@undoable
def get_tool_group(name, query_only=False, path_only=False):
    """Retrieve the tool's main group.

    If it doesn't exist, it will be created (unless `query_only` or `path_only` is `True`).
    """
    grp_path = f'|{TOOLS_ROOT_GRP_NAME}|{name}'
    icon_path = os.path.join(ICONS_PATH, f'{name}.svg')

    if path_only:
        return grp_path

    if cmds.objExists(grp_path):
        return grp_path

    if query_only:
        return None

    cmds.createNode('transform', name=name, parent=get_main_group(), skipSelect=True)

    if os.path.exists(icon_path):
        _set_node_icon(grp_path, icon_path)

    for attr_name in ['t', 'r', 's']:
        for axis in ['x', 'y', 'z']:
            cmds.setAttr(
                f'{grp_path}.{attr_name}{axis}',
                lock=True,
                keyable=False,
                channelBox=False,
            )

    cmds.setAttr(f'{grp_path}.visibility', keyable=False, channelBox=True)

    return grp_path


def _set_node_icon(grp, icon):
    selection_list = om_old.MSelectionList()
    mobj = om_old.MObject()

    selection_list.add(grp)
    selection_list.getDependNode(0, mobj)

    om_old.MFnDependencyNode(mobj).setIcon(os.path.join(ICONS_PATH, icon))
