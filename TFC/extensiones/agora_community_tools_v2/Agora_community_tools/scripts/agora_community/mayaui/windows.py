from functools import partial

from maya import cmds

from agora_community import qtui

from .utils import addWidgetToMayaLayout


def dockableWindow(cls=None, launcher=None, initialWidth=300, initialHeight=300):
    """Class decorator to allow windows to be docked into Maya.

    Warnings:
        - show/hide/close methods are overridden and the originals are never called
        - closeEvent method is not called when the window gets closed (use `onClose` instead)
    """
    if not cls:
        return partial(
            dockableWindow,
            launcher=launcher,
            initialWidth=initialWidth,
            initialHeight=initialHeight,
        )

    cls = qtui.singletonWidget(cls)

    originalInit = cls.__init__
    workspaceName = '{}.{}_workspaceControl'.format(cls.__module__, cls.__name__)

    def __init__(self, *args, **kwargs):
        try:
            originalInit(self, *args, **kwargs)
        except Exception as error:
            # delete the widget to not have it returned by the singleton widget
            self.deleteLater()

            raise error

        if not self.objectName():
            self.setObjectName('{}.{}'.format(self.__class__.__module__, self.__class__.__name__))

    def show(self):
        # original/super() not called by intent.
        if cmds.workspaceControl(workspaceName, query=True, exists=True):
            cmds.workspaceControl(workspaceName, edit=True, restore=True)
        else:
            if launcher:
                uiScript = 'from {0} import {1};{1}()'.format(
                    launcher.__module__,
                    launcher.__name__,
                )
            else:
                uiScript = 'from {0} import {1};{1}().show()'.format(
                    self.__class__.__module__,
                    self.__class__.__name__,
                )

            closeCommand = (
                'from {0} import {1};{1}().onClose() if hasattr({1}(), "onClose") else None'.format(
                    self.__class__.__module__,
                    self.__class__.__name__,
                )
            )

            cmds.workspaceControl(
                workspaceName,
                label=self.windowTitle(),
                retain=False,
                loadImmediately=False,
                restore=True,
                closeCommand=closeCommand,
                initialWidth=initialWidth,
                initialHeight=initialHeight,
            )

            # set the `uiScript` separately to not have it executed,
            # causing the launcher to be called two times.
            cmds.workspaceControl(workspaceName, edit=True, uiScript=uiScript)

        addWidgetToMayaLayout(self.objectName(), workspaceName, True)

    def hide(_self):
        # original/super() not called by intent.
        if cmds.workspaceControl(workspaceName, query=True, exists=True):
            cmds.workspaceControl(workspaceName, edit=True, visible=False)

    def close(_self):
        # original/super() not called by intent.
        if cmds.workspaceControl(workspaceName, query=True, exists=True):
            cmds.workspaceControl(workspaceName, edit=True, close=True)

            return True

        return False

    cls.__init__ = __init__
    cls.show = show
    cls.hide = hide
    cls.close = close

    return cls
