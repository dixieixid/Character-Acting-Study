import os
import logging

logging.basicConfig(level=logging.INFO)

LOGGER = logging.getLogger('Motion Trail')

TOOL_NAME = os.path.basename((os.path.dirname(__file__)))
TOOL_TITLE = 'Motion Trail'

RESOURCE_DIRECTORY = os.path.join(os.path.dirname(__file__), '_resources')
REFRESHRATE = 2

__all__ = [
    'LOGGER',
    'TOOL_NAME',
    'TOOL_TITLE',
    'RESOURCE_DIRECTORY',
    'REFRESHRATE',
]
