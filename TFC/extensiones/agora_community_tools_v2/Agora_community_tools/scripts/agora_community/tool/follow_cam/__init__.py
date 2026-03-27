"""Package for the Follow Cam tool."""

from . import core
from .constants import TOOL_TITLE

__tool_title__ = TOOL_TITLE


def launch():
    """Launch the Follow Cam tool."""
    core.create_follow_camera()


def extra_actions():
    """Declare the secondary actions."""
    return [
        ('Translate and Rotate', lambda: core.create_follow_camera(translate_only=False)),
        ('Translate Horizontally', lambda: core.create_follow_camera(ignore_up_axis=True)),
        ('Delete All', core.delete_all_follow_cameras),
    ]
