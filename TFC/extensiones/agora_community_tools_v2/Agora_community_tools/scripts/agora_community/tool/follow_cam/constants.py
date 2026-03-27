import os
import logging

logging.basicConfig(level=logging.INFO)

LOGGER = logging.getLogger('Follow Cam')

TOOL_NAME = os.path.basename((os.path.dirname(__file__)))
TOOL_TITLE = 'Follow Cam'

__all__ = [
    'LOGGER',
    'TOOL_NAME',
    'TOOL_TITLE',
]
