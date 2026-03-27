import os
import logging

TOOLS_VERSION = '1.0.0-beta'

LOGGER = logging.getLogger('Agora Community')

ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..'))
ICONS_PATH = os.path.join(ROOT_PATH, 'icons')

SHELF_NAME = 'Agora_Community'
SHELF_PATH = os.path.join(ROOT_PATH, 'shelves', f'shelf_{SHELF_NAME}.mel')

PACKAGE_NAME = 'agora_community'
MAIN_MENU_NAME = 'agora_community_main_menu'
MAIN_MENU_LABEL = 'Agora Community'

DOCS_URL = 'https://agora.community/assets?category=assets&resource=agora-studio-maya-tools'

AGORA_STUDIO_URL = 'https://agora.studio'
AGORA_COMMUNITY_HOME_URL = 'https://agora.community/home'
AGORA_COMMUNITY_ASSETS_URL = 'https://agora.community/assets'
AGORA_COMMUNITY_GITHUB_URL = ''
AGORA_COMMUNITY_DISCORD_URL = 'https://discord.gg/9hJxMyR'

USER_DIR_NAME = 'agora_community'
SETTINGS_DIR_NAME = 'settings'

TOOLS_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'tool')
TOOLS_IMPORT_PATH = f'{PACKAGE_NAME}.tool'
TOOLS_ROOT_GRP_NAME = 'AGORA_COMMUNITY'
TOOLS_ROOT_GRP_COLOR = (0.142, 0.658, 0.875)
TOOLS_ROOT_GRP_ICON = 'agora_community_logo.png'
