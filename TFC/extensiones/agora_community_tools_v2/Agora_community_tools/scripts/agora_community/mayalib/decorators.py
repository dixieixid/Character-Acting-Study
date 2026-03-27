"""Various decorators."""

import functools

from maya import cmds


def undoable(func):
    """Allow an entire function/method to be undoed."""

    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
        try:
            cmds.undoInfo(openChunk=True, chunkName=func.__name__)

            # Do an undoable action to have something to undo if the function does nothing.
            cmds.setAttr('time1.frozen', cmds.getAttr('time1.frozen'))

            return func(*args, **kwargs)
        finally:
            cmds.undoInfo(closeChunk=True, chunkName=func.__name__)

    return func_wrapper
