import os
import shutil
import maya.cmds as cmds
import maya.OpenMaya as om
from pathlib import Path

package_name = "DigetMirrorControl"
icon_name = "MirrorControlIcon.png"
shelf_button_name = "Diget Mirror Control"


def onMayaDroppedPythonFile(*args, **kwargs):
    installer_file = __file__
    source_path = Path(installer_file).parent

    install_package(source_path, package_name, installer_file)
    create_shelf_button(icon_name, package_name)


def install_package(source_path, package_name, installer_file):
    """
    copying files from folder with package to
    %USERPROFILE%/Documents/maya/scripts/<package_name>.
    """
    maya_app_dir = cmds.internalVar(userAppDir=1)

    # Joining Path to form destination folder path
    destination_base_path = Path(maya_app_dir) / "scripts" / package_name

    if source_path == destination_base_path:
        return

    for root, dirs, files in os.walk(source_path):
        relative_path = Path(root).relative_to(source_path)
        destination_path = Path(destination_base_path) / relative_path

        destination_path.mkdir(exist_ok=True)

        for file in files:
            source_file = Path(root) / file
            destination_file = Path(destination_path) / file

            shutil.copy(source_file, destination_file)
            om.MGlobal.displayInfo(
                f"File copied from: {source_file} to {destination_file}"
            )


def create_shelf_button(icon_name, package_name):
    """
    copying the icon to the icons path, adding shelf item'
    """

    maya_app_dir = cmds.internalVar(userAppDir=1)
    icons_path = Path(maya_app_dir) / "scripts" / package_name / "icons"

    current_shelf_tab = cmds.tabLayout("ShelfLayout", query=True, selectTab=True)

    shelf_command = (
        f"import {package_name}.main\n"
        f"{package_name}.main.main()"
    )

    shelf_icon = Path(icons_path) / icon_name

    if not shelf_icon.exists():
        om.MGlobal.displayWarning(f"Warning: Icon file not found at: {shelf_icon}")
        shelf_icon = "commandButton.png"

    cmds.shelfButton(
        label=shelf_button_name,
        command=shelf_command,
        image=shelf_icon,
        parent=current_shelf_tab,
        annotation=f"{shelf_button_name} Command",
    )
    om.MGlobal.displayInfo(
        f"Shelf Button '{shelf_button_name}' has been "
        f"Created on '{current_shelf_tab}' Shelf."
    )
