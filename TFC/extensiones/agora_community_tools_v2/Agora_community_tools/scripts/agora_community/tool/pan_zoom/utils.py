"""Utility functions."""

from maya.api import OpenMayaUI as omui

from agora_community.vendor import mayax as mx


def get_active_camera():
    """Retrieve the active camera."""
    return mx.Node(str(omui.M3dView().active3dView().getCamera())).parent


def get_camera_view_direction(camera):
    """Retrieve the camera's view direction."""
    mtx = camera.worldMatrix

    return -mx.Vector(mtx[8], mtx[9], mtx[10])  # negative Z-axis


def get_world_position(obj):
    """Retrieve the object's world position.

    TODO: MayaX's `obj.worldPosition` doesn't work correctly for frozen objects.
    Once fixed, this function shouldn't be necessary.
    """
    return mx.Vector(mx.cmd.xform(obj, query=True, rotatePivot=True, worldSpace=True))


def get_objects_center(objects):
    """Retrieve the objects' center position."""
    center = mx.Vector()

    for obj in objects:
        center += get_world_position(obj)

    return center / len(objects)


def get_matrix_position(matrix):
    """Retrieve the matrix position."""
    return mx.Vector(matrix[12], matrix[13], matrix[14])


def set_matrix_position(matrix, position):
    """Update the matrix position."""
    matrix[12] = position.x
    matrix[13] = position.y
    matrix[14] = position.z


@mx.undoable
def create_angle_between_node(vector_attr_1, vector_attr_2, name='angleBetween'):
    """Create an angleBetween node and make the proper connections."""
    node = mx.cmd.createNode('angleBetween', name=name, skipSelect=True)
    vector_attr_1.connect(node['vector1'])
    vector_attr_2.connect(node['vector2'])

    return node


@mx.undoable
def create_cos_node(angle_attr, name='cos'):
    """Create a cos node using eulerToQuat.

    Use the `outputQuatW` attribute to retrieve the cos value from the node.
    (see https://www.chadvernon.com/blog/trig-maya/)
    """
    cos_node = mx.cmd.createNode('eulerToQuat', name=name, skipSelect=True)
    angle_node = mx.cmd.createNode(
        'multDoubleLinear', name=name + '__doubledAngle', skipSelect=True
    )

    angle_node.input1 = 2
    angle_attr.connect(angle_node['input2'])

    angle_node['output'].connect(cos_node['inputRotateX'])

    return [cos_node, angle_node]


@mx.undoable
def create_scaled_vector_node(vector_attr, distance_attr, name='scaledVector'):
    """Scale a vector.

    Use `output` attribute for result.
    """
    normalize_node = mx.cmd.createNode('vectorProduct', name=name + '__normalized', skipSelect=True)
    normalize_node.operation = 0  # no operation
    normalize_node.normalizeOutput = True
    vector_attr.connect(normalize_node['input1'])

    output_node = mx.cmd.createNode('multiplyDivide', name=name, skipSelect=True)
    output_node.operation = 1  # multiply
    normalize_node['output'].connect(output_node['input1'])
    distance_attr.connect(output_node['input2X'])
    distance_attr.connect(output_node['input2Y'])
    distance_attr.connect(output_node['input2Z'])

    return [output_node, normalize_node]
