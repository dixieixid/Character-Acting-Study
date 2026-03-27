import os
import logging

logging.basicConfig(level=logging.INFO)

LOGGER = logging.getLogger('Mirror Cam')

TOOL_NAME = os.path.basename((os.path.dirname(__file__)))
TOOL_TITLE = 'Mirror Cam'

__all__ = [
    'LOGGER',
    'TOOL_NAME',
    'TOOL_TITLE',
]
