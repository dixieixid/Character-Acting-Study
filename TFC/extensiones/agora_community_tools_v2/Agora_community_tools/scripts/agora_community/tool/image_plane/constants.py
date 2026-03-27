import os
import logging

logging.basicConfig()

LOGGER = logging.getLogger('Image Plane')

TOOL_NAME = os.path.basename((os.path.dirname(__file__)))
TOOL_TITLE = 'Image Plane'
TOOL_STYLE_PATH = os.path.join(os.path.dirname(__file__), '_resources', 'style.qss')

SUPPORTED_FILE_EXTS = [
    '.jpg',
    '.jpeg',
    '.png',
    '.bmp',
    '.tif',
    '.tiff',
    '.gif',
    '.mov',
    '.mkv',
    '.mp4',
    '.avi',
]

VIDEO_FILE_EXTS = [
    '.mov',
    '.mkv',
    '.mp4',
    '.avi',
]

__all__ = [
    'LOGGER',
    'TOOL_NAME',
    'TOOL_TITLE',
    'TOOL_STYLE_PATH',
    'SUPPORTED_FILE_EXTS',
    'VIDEO_FILE_EXTS',
]
