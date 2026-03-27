"""Various context managers."""

import contextlib

from maya import cmds


@contextlib.contextmanager
def undo_skip():
    """Skip adding the encapsulated commands to the undo queue."""
    undo_state = cmds.undoInfo(query=True, stateWithoutFlush=True)

    cmds.undoInfo(stateWithoutFlush=False)

    try:
        yield
    finally:
        cmds.undoInfo(stateWithoutFlush=undo_state)
