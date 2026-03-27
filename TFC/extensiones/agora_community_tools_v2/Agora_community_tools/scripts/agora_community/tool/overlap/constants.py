import os
import logging

logging.basicConfig(level=logging.INFO)

LOGGER = logging.getLogger('Overlap')

TOOL_NAME = os.path.basename((os.path.dirname(__file__)))
TOOL_TITLE = 'Overlap'

DEFAULT_BAKE_OPTION_DG = True
DEFAULT_BAKE_OPTION_SIMULATE = True

__all__ = [
    'LOGGER',
    'TOOL_NAME',
    'TOOL_TITLE',
    'DEFAULT_BAKE_OPTION_DG',
    'DEFAULT_BAKE_OPTION_SIMULATE',
]
