import os
import logging

logging.basicConfig(level=logging.INFO)

LOGGER = logging.getLogger('Anim Tweener')

TOOL_NAME = os.path.basename((os.path.dirname(__file__)))
TOOL_TITLE = 'Anim Tweener'

RESOURCE_DIRECTORY = os.path.join(os.path.dirname(__file__), '_resources')
SUPPORTED_MODS = [0, 1, 4, 9]

"""
Mods lexicon:
0 = Normal
1 = Shift
4 = Ctrl
9 = Alt + Shift
"""

__all__ = [
    'LOGGER',
    'TOOL_NAME',
    'TOOL_TITLE',
    'RESOURCE_DIRECTORY',
    'SUPPORTED_MODS',
]
