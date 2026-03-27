"""Utility functions."""

import os

from agora_community.vendor import mayax as mx

from .constants import VIDEO_FILE_EXTS


def get_active_camera():
    """Retrieve the active camera."""
    camera = mx.cmd.lookThru(query=True)
    if not camera:
        raise None

    if camera.type != 'transform':
        camera = camera.parent

    return camera


def get_all_cameras():
    """Retrieve all cameras."""
    return [obj.parent for obj in mx.cmd.ls(type='camera')]


def get_image_plane_camera(node):
    """Retrieve the camera for the image plane."""
    camera = mx.cmd.imagePlane(node, query=True, camera=True)[0] or None
    if camera and camera.type != 'transform':
        camera = camera.parent

    return camera


def get_animation_range():
    """Retrieve the animation's time range."""
    return (
        mx.cmd.playbackOptions(query=True, animationStartTime=True),
        mx.cmd.playbackOptions(query=True, animationEndTime=True),
    )


def get_playback_range():
    """Retrieve the playback's time range."""
    return (
        mx.cmd.playbackOptions(query=True, minTime=True),
        mx.cmd.playbackOptions(query=True, maxTime=True),
    )


def is_video_file(file_path):
    """Check if a file is a video file."""
    return os.path.splitext(file_path)[-1].lower() in VIDEO_FILE_EXTS
