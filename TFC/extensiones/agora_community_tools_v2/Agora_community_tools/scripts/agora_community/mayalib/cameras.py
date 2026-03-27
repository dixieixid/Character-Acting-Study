from maya import cmds


def get_camera_shape(camera):
    """
    Get the camera shape from <camera>.

    Args:
        camera (str): The name of the camera or camera transform.

    Returns:
        str: The camera shape name.

    Raises:
        ValueError: If camera is not a camera or camera transform.
    """
    if cmds.nodeType(camera) == 'camera':
        return camera
    elif cmds.nodeType(camera) != 'transform':
        raise ValueError('"{}" is not a Camera or a Camera '
                         'transform :: "{}".'.format(camera, cmds.nodeType(camera)))

    return cmds.listRelatives(camera, shapes=True, type='camera', path=True)[0]


def is_film_gate_active(camera):
    """
    Checks if the film gate is active for the specified camera.

    Args:
        camera (str): The name of the camera.

    Returns:
        bool: True if the film gate is active, False otherwise.
    """
    camera_shape = get_camera_shape(camera)
    return cmds.getAttr('{}.displayFilmGate'.format(camera_shape))


def is_resolution_gate_active(camera):
    """
    Checks if the resolution gate is active for the specified camera.

    Args:
        camera (str): The name of the camera.

    Returns:
        bool: True if the resolution gate is active, False otherwise.
    """
    camera_shape = get_camera_shape(camera)
    return cmds.getAttr('{}.displayResolution'.format(camera_shape))
