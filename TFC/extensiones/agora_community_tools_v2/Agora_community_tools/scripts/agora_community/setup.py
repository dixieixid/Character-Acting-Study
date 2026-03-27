"""Setup functionality."""

import os
import importlib
import webbrowser
from functools import partial

from maya import cmds, mel

from agora_community.constants import *
from agora_community.about_prompt import about_ui


def main(first_run=False):
    """Setup the tools."""
    create_main_menu()
    register_tools()
    community_submenu()
    load_main_shelf(activate=first_run)


def create_main_menu():
    """Create the main menu."""
    if not cmds.menu(MAIN_MENU_NAME, exists=True):
        cmds.menu(
            MAIN_MENU_NAME,
            label=MAIN_MENU_LABEL,
            parent='MayaWindow',
            tearOff=True,
        )


def open_web_browser(url):
    """Open a web browser with the given URL."""
    try:
        webbrowser.open(url, new=2)  # new=2 tries to open in a new tab, if possible
        print(f"Opening URL: {url}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Failed to open URL: {e}")


def register_tools():
    """Register the tools."""

    def _on_menu_item_cmd(cmd_fn, _checked):
        cmd_fn()

    cmds.menuItem(
        label='Tools',
        parent=MAIN_MENU_NAME,
        divider=True,
    )

    for tool_name in os.listdir(TOOLS_PATH):
        tool_module = importlib.import_module(f'{TOOLS_IMPORT_PATH}.{tool_name}')
        tool_title = tool_module.__tool_title__
        tool_icon = os.path.join(ICONS_PATH, f'{tool_name}.svg')

        try:
            tool_extra_actions = tool_module.extra_actions()
        except AttributeError:
            tool_extra_actions = []

        if tool_extra_actions:
            cmds.menuItem(
                parent=MAIN_MENU_NAME,
                label=tool_title,
                image=tool_icon,
                subMenu=True,
            )
            cmds.menuItem(
                label=tool_title,
                command=partial(_on_menu_item_cmd, tool_module.launch),
            )

            for action_name, action_fn in tool_extra_actions:
                cmds.menuItem(
                    label=action_name,
                    command=partial(_on_menu_item_cmd, action_fn),
                )
        else:
            cmds.menuItem(
                parent=MAIN_MENU_NAME,
                label=tool_title,
                image=tool_icon,
                command=partial(_on_menu_item_cmd, tool_module.launch),
            )


def community_submenu():
    """Create community links."""
    if not cmds.menu(MAIN_MENU_NAME, exists=True):
        return

    # Agora community label
    cmds.menuItem(
        label='Info',
        parent=MAIN_MENU_NAME,
        divider=True,
    )

    # Agora community submenu
    cmds.menuItem(
        label='Resources',
        subMenu=True,
        parent=MAIN_MENU_NAME,
        image='agora_community_logo.png',
    )

    cmds.menuItem(
        label='Home Page',
        image='agora_community_logo.png',
        command=lambda _:(
            open_web_browser(url=AGORA_COMMUNITY_HOME_URL)
        )
    )

    cmds.menuItem(
        label='Tools Page',
        image='agora_community_logo.png',
        command=lambda _:(
            open_web_browser(url=DOCS_URL)
        )
    )

    cmds.menuItem(
        label='Download Agora\'s Original Characters',
        image='agora_community_logo.png',
        command=lambda _:(
            open_web_browser(url=AGORA_COMMUNITY_ASSETS_URL)
        )
    )

    cmds.menuItem(
        label='Join Discord',
        image='Discord-Symbol-Light Blurple.svg',
        command=lambda _:(
            open_web_browser(url=AGORA_COMMUNITY_DISCORD_URL)
        )
    )

    cmds.setParent(MAIN_MENU_NAME, menu=True)

    cmds.menuItem(
        label='About...',
        image='menuIconHelp.png',
        command=lambda _: about_ui.launch()  # Launch the AboutWindow
    )


def load_main_shelf(activate=False):
    """Load the main shelf."""
    try:
        selected_shelf_tab = mel.eval('shelfTabLayout -q -selectTab $gShelfTopLevel')
    except RuntimeError:
        selected_shelf_tab = ''

    try:
        if cmds.shelfLayout(SHELF_NAME, exists=True):
            mel.eval(f'deleteUI -layout ($gShelfTopLevel + "|{SHELF_NAME}");')
    except RuntimeError:
        pass

    mel.eval(f'loadNewShelf "{SHELF_PATH}";'.replace('\\', '/'))

    if not activate and selected_shelf_tab:
        try:
            mel.eval(f'shelfTabLayout -e -selectTab "{selected_shelf_tab}" $gShelfTopLevel')
        except RuntimeError:
            pass
