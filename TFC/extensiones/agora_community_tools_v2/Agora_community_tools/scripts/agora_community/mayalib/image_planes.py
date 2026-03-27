import glob
import os
import re

from maya import cmds

from ..constants import LOGGER
from ..lib import ensure_iterable
from .scene import get_parent


IMAGE_SEQUENCE_FILENAME_PATTERN = re.compile(r'(.*?\.)(\d+)?')


class FilmFitType:
    Fill = 0
    Horizontal = 1
    Vertical = 2
    OverScan = 3


def get_model_panel_image_planes_visibility(panels=None):
    """
    Get image plane visibility states for <panels>.

    Args:
        panels (list[str]|str|None): ModelPanel(s) to query. None to query all.

    Returns:
        dict[str, bool]: Dictionary of modelPanel name and image plan visibility state.
    """
    results = {}
    panels = panels or cmds.getPanel(type='modelPanel')
    panels = ensure_iterable(panels)
    for panel in panels:
        results[panel] = cmds.modelEditor(panel, query=True, imagePlane=True)
    return results


def set_model_panel_image_planes_visibility(panel_states):
    """
    Set image plane visibility states for <panels>.

    Args:
        panel_states (dict[str, bool]): Dictionary of modelPanel name and image plan visibility state.
    """
    for panel, state in panel_states.items():
        cmds.modelEditor(panel, edit=True, imagePlane=state)


def hide_image_planes(panels=None):
    """
    Hide image plane visibility for <panels>.

    Args:
        panels (list[str]|str|None): ModelPanel(s) to affect. None to affect all.
    """
    data = {
        panel: False
        for panel in get_model_panel_image_planes_visibility(panels=panels)
    }
    set_model_panel_image_planes_visibility(data)


def show_image_planes(panels=None):
    """
    Show image plane visibility for <panels>.

    Args:
        panels (list[str]|str|None): ModelPanel(s) to affect. None to affect all.
    """
    data = {
        panel: True
        for panel in get_model_panel_image_planes_visibility(panels=panels)
    }
    set_model_panel_image_planes_visibility(data)


def get_camera_from_image_plane(image_plane):
    """
    Get camera from <image_plane>.
    The camera transform is given.

    Args:
        image_plane (str): Image plane to use.

    Returns:
        str|None: Camera name or None.
    """
    cameras = cmds.imagePlane(image_plane, query=True, camera=True)
    if not cameras:
        return None

    camera = cameras[0]
    if cmds.nodeType(camera) != 'transform':
        camera = get_parent(camera)
    return camera


def fit_image_plane_to_film_gate(image_plane):
    """
    Adjust <image_plane> size to match <camera>'s film aperture.
    # AEimagePlaneTemplate.mel

    Args:
        image_plane (str): The image plane to fit.
    """
    camera = get_camera_from_image_plane(image_plane)
    if not camera:
        raise RuntimeError('Image plane is not assigned to a camera.')

    cam_x = cmds.getAttr(camera + '.horizontalFilmAperture')
    cam_y = cmds.getAttr(camera + '.verticalFilmAperture')

    cmds.setAttr(image_plane + '.sizeX', cam_x)
    cmds.setAttr(image_plane + '.sizeY', cam_y)


def fit_image_plane_to_resolution_gate(image_plane):
    """
    Adjusts the <image_plane> resolution size to fit its camera's film aperture.
    # AEimagePlaneTemplate.mel

    Args:
        image_plane (str): The image plane to fit.
    """
    camera = get_camera_from_image_plane(image_plane)
    if not camera:
        raise RuntimeError('Image plane is not assigned to a camera.')

    size_x_attr = image_plane + '.sizeX'
    size_y_attr = image_plane + '.sizeY'

    # Get resolution info
    globals_list = cmds.ls(type='renderGlobals')
    rez = cmds.listConnections(globals_list[0] + '.resolution')
    rez_aspect = cmds.getAttr(rez[0] + '.deviceAspectRatio')

    cam_x = cmds.getAttr(camera + '.horizontalFilmAperture')
    cam_y = cmds.getAttr(camera + '.verticalFilmAperture')
    fit_type = cmds.getAttr(camera + '.filmFit')

    # Based on camera + resolution info, provide best fit.
    if fit_type == FilmFitType.Fill:
        cam_aspect = cam_x / cam_y
        if rez_aspect < cam_aspect:
            cmds.setAttr(size_y_attr, cam_y)
            cmds.setAttr(size_x_attr, cam_y * rez_aspect)
        else:
            cmds.setAttr(size_x_attr, cam_x)
            cmds.setAttr(size_y_attr, cam_x / rez_aspect)
    elif fit_type == FilmFitType.Horizontal:
        cmds.setAttr(size_x_attr, cam_x)
        cmds.setAttr(size_y_attr, cam_x / rez_aspect)
    elif fit_type == FilmFitType.Vertical:
        cmds.setAttr(size_y_attr, cam_y)
        cmds.setAttr(size_x_attr, cam_y * rez_aspect)
    elif fit_type == FilmFitType.OverScan:
        cam_aspect = cam_x / cam_y
        if rez_aspect < cam_aspect:
            cmds.setAttr(size_x_attr, cam_x)
            cmds.setAttr(size_y_attr, cam_x / rez_aspect)
        else:
            cmds.setAttr(size_x_attr, cam_y * rez_aspect)
            cmds.setAttr(size_y_attr, cam_y)


def is_image_sequence(filepath):
    """
    Get if <filepath> is an image sequence.

    Args:
        filepath (str): The filepath to check.

    Returns:
        bool: True if <filepath> is an image sequence.
    """
    directory, filename = os.path.split(filepath)
    basename, ext = os.path.splitext(filename)

    match = IMAGE_SEQUENCE_FILENAME_PATTERN.match(basename)
    return match is not None


def get_image_sequence(filepath, check_sequential=True):
    """
    Get image sequence from <filepath>.

    Args:
        filepath (str): The image file path.
        check_sequential (bool): True to only return if
            images are sequential.

    Returns:
        list[str]: List of image file paths.

    Raises:
        ValueError: If <filepath> is not a potential image sequence.
    """
    directory, filename = os.path.split(filepath)
    if not is_image_sequence(filepath):
        raise ValueError('"{}" is not a valid image sequence.'.format(filename))

    basename, ext = os.path.splitext(filename)
    match = IMAGE_SEQUENCE_FILENAME_PATTERN.match(basename)
    name_part = match.group(1)
    digits = match.group(2)

    glob_filename_pattern = '{name}{digits}{ext}'.format(
        name=name_part,
        digits='[0-9]' * len(digits),
        ext=ext,
    )
    glob_pattern = os.path.join(directory, glob_filename_pattern)

    LOGGER.debug('Searching image sequence with "{}"...'.format(glob_pattern))
    results = sorted(glob.glob(glob_pattern))

    # Extract the numbers from results filepath and check
    # they're sequential.
    if check_sequential:
        numbers = []
        for i, result in enumerate(results):
            basename = os.path.basename(result)
            match = IMAGE_SEQUENCE_FILENAME_PATTERN.match(
                os.path.splitext(basename)[0]
            )
            if match and match.group(1) == name_part:
                numbers.append(int(match.group(2)))
                if i and numbers[i] != numbers[i - 1] + 1:
                    LOGGER.debug('"{}" found not sequential from '
                                 'previous index ({}).'.format(basename, numbers[i - 1]))
                    return []

    return results
