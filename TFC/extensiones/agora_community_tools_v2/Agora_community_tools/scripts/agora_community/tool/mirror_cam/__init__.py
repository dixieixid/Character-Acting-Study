"""Package for the Mirror Cam tool."""

from . import core
from .constants import TOOL_TITLE

__tool_title__ = TOOL_TITLE


def launch():
    """Launch the Mirror Cam tool."""
    core.create_mirror_camera()
