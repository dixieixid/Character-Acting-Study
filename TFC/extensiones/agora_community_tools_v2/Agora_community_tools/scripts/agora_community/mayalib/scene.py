from maya import cmds


def get_parent(node):
    """
    Return the parent of the given node.

    Args:
        node (str): Node to use.

    Returns:
        (str, None): Node parent, if any.
    """
    try:
        return cmds.listRelatives(node, path=True, parent=True)[0]

    except (IndexError, TypeError):
        return None

