"""Functions to open custom modal dialogs."""

from . import qt


def warningDialog(title, text, parent=None):
    """Open a warning dialog."""
    qt.QMessageBox.warning(
        parent,
        title,
        text,
        qt.QMessageBox.Ok,
    )


def confirmDialog(title, text, parent=None):
    """Open a confirmation dialog."""
    return (
        qt.QMessageBox.warning(
            parent,
            title,
            text,
            qt.QMessageBox.Yes | qt.QMessageBox.No,
        )
        == qt.QMessageBox.Yes
    )


def inputDialog(title, label, text='', parent=None, strip=True, accept_empty=True):
    """Get data from the user.

    Returns:
        entered text or None on cancel
    """
    text, ok = qt.QInputDialog.getText(parent, title, label, text=text)

    if not ok:
        return None

    if strip:
        text = text.strip()

    if not text and not accept_empty:
        text = inputDialog(title, label, text, parent, strip, accept_empty)

    return text
