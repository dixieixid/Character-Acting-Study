"""Anim controls functionality."""

import os
import json

from agora_community.vendor import mayax as mx

from ..constants import *
from .types import CtrlType
from .general import get_root_grp, get_temp_grp
from . import utils


_CTRL_ATTR = 'anim_locator_ctrl'


@mx.undoable
def create_ctrl(
    name,
    ctrl_type,
    ctrl_color,
    target=None,
    parent=None,
    with_buffer=False,
    rotation=None,
):
    """Create a control."""
    ctrl_path = os.path.join(CTRL_TYPES_PATH, CtrlType.name(ctrl_type) + '.json')
    ctrl_parent = parent if parent else get_root_grp()

    with open(ctrl_path, 'r') as file:
        curve_data = json.load(file)

    ctrl = mx.cmd.curve(
        degree=curve_data['degree'],
        knot=curve_data['knots'],
        point=curve_data['points'],
    )
    ctrl.name = name  # set the name separately to automatically rename the shape

    if rotation:
        ctrl.worldRotation = rotation
        ctrl.freezeTransform()

    for attr_name in ['sx', 'sy', 'sz']:
        mx.cmd.setAttr(ctrl[attr_name], channelBox=True, keyable=False)

    ctrl_attr = ctrl.addAttr(_CTRL_ATTR, True)
    ctrl_attr.locked = True

    ctrl.addAttr('buffer', type=mx.Node)
    ctrl.addAttr('target', type=mx.Node)

    if with_buffer:
        buffer = mx.cmd.createNode(
            'transform',
            name=name + 'Buffer',
            parent=ctrl_parent,
            skipSelect=True,
        )
        ctrl.buffer = buffer
        ctrl.parent = buffer
    else:
        buffer = None
        ctrl.parent = ctrl_parent

    if target:
        ctrl.target = target

        if buffer:
            mx.cmd.matchTransform(buffer, target, position=True, rotation=True)
        else:
            mx.cmd.matchTransform(ctrl, target, position=True, rotation=True)

        radius = utils.get_bbox_average_radius(target) * CTRL_RADIUS_MULTIPLIER
        ctrl.worldScale = [radius, radius, radius]

    change_ctrls_color([ctrl], ctrl_color)

    return ctrl


@mx.undoable
def create_temp_ctrl(name, ctrl_type, ctrl_color, target=None, with_buffer=False, rotation=None):
    """Create a temporary control."""
    return create_ctrl(name, ctrl_type, ctrl_color, target, get_temp_grp(), with_buffer, rotation)


@mx.undoable
def make_temp_ctrl_permanent(temp_ctrl, ignore_buffer=False):
    """Make the temporary control permanent."""
    if temp_ctrl.buffer and not ignore_buffer:
        temp_ctrl.buffer.parent = get_root_grp()
    else:
        temp_ctrl.parent = get_root_grp()

    temp_grp = get_temp_grp(query_only=True)

    if temp_grp and not temp_grp.children:
        temp_grp.delete()


def is_ctrl(obj):
    """Check if the provided object is a control."""
    return obj.hasAttr(_CTRL_ATTR)


def is_temp_ctrl(obj):
    """Check if the provided object is a temporary control."""
    return is_ctrl(obj) and '{}|{}'.format(TOOL_NAME, TEMP_GRP_NAME) in obj.pathName


def all_ctrls(ignore_temp_ctrls=True):
    """Retrieve all the controls found in the scene."""
    root_grp = get_root_grp(query_only=True)

    if not root_grp:
        return []

    return [
        obj
        for obj in root_grp.descendents
        if is_ctrl(obj) and (not ignore_temp_ctrls or not is_temp_ctrl(obj))
    ]


def all_temp_ctrls():
    """Retrieve all the temporary controls found in the scene."""
    temp_grp = get_temp_grp(query_only=True)

    if not temp_grp:
        return []

    return [obj for obj in temp_grp.descendents if is_ctrl(obj)]


@mx.undoable
def change_ctrls_type(ctrls, ctrl_type):
    """Change the controls' color.

    If `ctrls` is `None` the selected objects will be used instead.
    """
    if ctrls is None:
        ctrls = mx.cmd.ls(selection=True, transforms=True)

    ctrl_path = os.path.join(CTRL_TYPES_PATH, CtrlType.name(ctrl_type) + '.json')

    with open(ctrl_path, 'r') as file:
        curve_data = json.load(file)

    for ctrl in ctrls:
        if is_ctrl(ctrl):
            mx.cmd.curve(
                ctrl.shapes[0],
                replace=True,
                degree=curve_data['degree'],
                knot=curve_data['knots'],
                point=curve_data['points'],
            )


@mx.undoable
def change_ctrls_color(ctrls, color_index):
    """Change the controls' color.

    If `ctrls` is `None` the selected objects will be used instead.
    """
    if ctrls is None:
        ctrls = mx.cmd.ls(selection=True, transforms=True)

    for ctrl in ctrls:
        if is_ctrl(ctrl):
            utils.override_object_color(ctrl, color_index, first_shape_only=True)
