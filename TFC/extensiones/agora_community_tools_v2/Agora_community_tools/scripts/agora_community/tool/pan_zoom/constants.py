import os
import logging

logging.basicConfig(level=logging.INFO)

LOGGER = logging.getLogger('Pan Zoom')

TOOL_NAME = os.path.basename((os.path.dirname(__file__)))
TOOL_TITLE = 'Pan Zoom'
TOOL_STYLE_PATH = os.path.join(os.path.dirname(__file__), '_resources', 'style.qss')

__all__ = [
    'LOGGER',
    'TOOL_NAME',
    'TOOL_TITLE',
    'TOOL_STYLE_PATH',
]
