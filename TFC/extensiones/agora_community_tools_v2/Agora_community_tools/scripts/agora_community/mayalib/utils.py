from maya import cmds


def user_directory():
    """Retrieve the user application directory."""
    return cmds.internalVar(userAppDir=True)
