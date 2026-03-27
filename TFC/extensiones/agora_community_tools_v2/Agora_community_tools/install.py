"""Drop this file in a Maya viewport to install the Agora Community tools."""

import os
import sys
import importlib
import shutil

from maya import cmds

PACKAGE_NAME = 'agora_community'
PACKAGE_TITLE = 'Agora Community'
MODULE_FILENAME = f'{PACKAGE_NAME}.mod'


def onMayaDroppedPythonFile(*_):
    """Install when the file is dropped in the viewport."""
    install()

    cmds.confirmDialog(
        title=PACKAGE_TITLE,
        message=f'<b>{PACKAGE_TITLE}</b> tools were <b>installed</b>.',
        button='OK',
        icon='information',
    )


def install():
    """Install the tools."""
    maya_modules_path = os.path.join(cmds.internalVar(userAppDir=True), 'modules')
    downloaded_path = os.path.dirname(os.path.realpath(__file__))
    installation_path = os.path.join(maya_modules_path, PACKAGE_NAME)
    installation_scripts_path = os.path.join(installation_path, 'scripts')
    installation_icons_path = os.path.join(installation_path, 'icons')

    downloaded_module_path = os.path.join(downloaded_path, MODULE_FILENAME)
    installation_module_path = os.path.join(maya_modules_path, MODULE_FILENAME)

    uninstall(installation_path, installation_module_path)

    os.makedirs(maya_modules_path, exist_ok=True)

    shutil.copytree(downloaded_path, installation_path)
    shutil.copyfile(downloaded_module_path, installation_module_path)

    if installation_scripts_path not in sys.path:
        sys.path.append(installation_scripts_path)

    current_icons_paths = os.environ.get('XBMLANGPATH', '')
    if installation_icons_path not in current_icons_paths:
        os.environ['XBMLANGPATH'] = installation_icons_path + os.pathsep + current_icons_paths

    importlib.import_module(f'{PACKAGE_NAME}.setup').main()


def uninstall(installation_path, installation_module_path):
    """Uninstall the tools."""
    if os.path.exists(installation_path):
        shutil.rmtree(installation_path)

    if os.path.exists(installation_module_path):
        os.remove(installation_module_path)
