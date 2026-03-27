import logging
import os

logging.basicConfig(level=logging.INFO)

LOGGER = logging.getLogger('Anim Locator')

RESOURCE_DIRECTORY = os.path.join(os.path.dirname(__file__), '_resources')
ICONS_DIRECTORY = os.path.join(RESOURCE_DIRECTORY, 'icons')

TOOL_NAME = os.path.basename((os.path.dirname(__file__)))
TOOL_TITLE = 'Anim Locator'
TOOL_STYLE_PATH = os.path.join(os.path.dirname(__file__), '_resources', 'style.qss')

TEMP_GRP_NAME = '__temp__'

TOO_MANY_OBJECTS_COUNT = 5

CTRL_TYPES_PATH = os.path.join(RESOURCE_DIRECTORY, 'ctrl_types')
CTRL_SUFFIX_WORLD = 'animWorld'
CTRL_SUFFIX_DETACHED = 'animDetached'
CTRL_SUFFIX_PIVOT = 'animPivot'
CTRL_SUFFIX_TARGET = 'animTarget'
CTRL_SUFFIX_AIM_FORWARD = 'animAimForward'
CTRL_SUFFIX_AIM_UP = 'animAimUp'
CTRL_COLORS_IGNORED = [
    16,  # white, objects' color
    19,  # light green, lead object's color
]
CTRL_RADIUS_MULTIPLIER = 1.2

DEFAULT_BAKE_OPTION_DG = True
DEFAULT_BAKE_OPTION_SIMULATE = False
DEFAULT_BAKE_OPTION_SMART = True
DEFAULT_CTRL_COLOR = 18  # cyan
DEFAULT_CTRL_TYPE = 3  # sphere

COLOR_RED = 13
COLOR_GREEN = 14
COLOR_BLUE = 6
COLOR_YELLOW = 22
COLOR_TAN = 21

ROTATE_ORDERS = ('xyz', 'yzx', 'zxy', 'xzy', 'yxz', 'zyx')

__all__ = [
    'LOGGER',
    'RESOURCE_DIRECTORY',
    'ICONS_DIRECTORY',
    'TOOL_NAME',
    'TOOL_TITLE',
    'TOOL_STYLE_PATH',
    'TEMP_GRP_NAME',
    'TOO_MANY_OBJECTS_COUNT',
    'CTRL_TYPES_PATH',
    'CTRL_SUFFIX_WORLD',
    'CTRL_SUFFIX_DETACHED',
    'CTRL_SUFFIX_PIVOT',
    'CTRL_SUFFIX_TARGET',
    'CTRL_SUFFIX_AIM_FORWARD',
    'CTRL_SUFFIX_AIM_UP',
    'CTRL_COLORS_IGNORED',
    'CTRL_RADIUS_MULTIPLIER',
    'DEFAULT_BAKE_OPTION_DG',
    'DEFAULT_BAKE_OPTION_SIMULATE',
    'DEFAULT_BAKE_OPTION_SMART',
    'DEFAULT_CTRL_COLOR',
    'DEFAULT_CTRL_TYPE',
    'COLOR_RED',
    'COLOR_GREEN',
    'COLOR_BLUE',
    'COLOR_YELLOW',
    'COLOR_TAN',
    'ROTATE_ORDERS',
]
