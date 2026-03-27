"""Maya will load this on startup."""

from maya import cmds

from agora_community import setup

cmds.evalDeferred(setup.main, lowestPriority=True)
