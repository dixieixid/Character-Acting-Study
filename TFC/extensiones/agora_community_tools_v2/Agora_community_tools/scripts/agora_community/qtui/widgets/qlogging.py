"""Module to provide basic convenience widgets to be used with the Python logging module."""

import logging
import collections.abc

from .. import qt

COLORS = {
    logging.NOTSET: qt.QColor('#888'),
    logging.DEBUG: qt.QColor('#99CEEE'),
    logging.INFO: qt.QColor('grey'),
    logging.WARNING: qt.QColor('#ffa700'),
    logging.ERROR: qt.QColor('#ff4a4a'),
    logging.CRITICAL: qt.QColor('#ff4a4a'),
}

_self_from_func = lambda func_: func_.__self__


def SafeLogSlotConnect(func):
    """
    Method to safely cleanup a log handler if the receiving widget is deleted.
    """

    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (RuntimeError, OSError) as e:
            message = str(e)
            if message.startswith('Internal C++ object (') and message.endswith(
                ') already deleted.'
            ):
                instance = _self_from_func(func)
                if instance:
                    remove_method = getattr(instance, 'removeHandler', None)
                    if remove_method is not None:
                        remove_method()

    return inner


def ensure_iterable(objects):
    """
    Convenience function to get <objects> ias an accepted iterable type.
    This is predominately useful when dealing with strings.

    Args:
        objects (any): Objects to ensure is iterable.

    Returns:
        any: Objects as an iterable.
    """
    if objects is None:
        return []

    if isinstance(objects, str):
        return [objects]
    elif isinstance(objects, collections.abc.Iterable):
        return objects
    return [objects]


class QRecordEmitter(qt.QObject):
    """
    QObject to handle log related signals.
    """

    recordReceived = qt.Signal(logging.LogRecord)


class QLogHandler(logging.Handler):
    """
    logging.Handler class whose instances emits to their assigned QWidget.
    """

    def __init__(self, *args, **kwargs):
        super(QLogHandler, self).__init__(*args, **kwargs)
        self._recordEmitter = QRecordEmitter()

        # Alias
        self.recordReceived = self._recordEmitter.recordReceived

    def emit(self, record):
        self.recordReceived.emit(record)


class LoggerQObjectMixin(object):
    """
    Mixin class to be used by QWidgets to receive log records.

    Args:
        log (logging.Logger|None): Log object to receive records for.
        colors (dict|None): Color overrides for log records.
    """

    def __init__(self, *args, **kwargs):
        # Remove the logger value, if given
        loggers = kwargs.pop('log', [])

        # Store complete set of colors
        colors = kwargs.pop('colors', {})
        if colors:
            self._recordColorMapping = COLORS.copy()
            self._recordColorMapping.update(colors)

        else:
            self._recordColorMapping = None

        super(LoggerQObjectMixin, self).__init__(*args, **kwargs)

        self.loggerHandler = QLogHandler()
        self.logRecordReceived = self.loggerHandler.recordReceived

        # Add the logger object (if given)
        if loggers:
            self.addLogs(loggers)

    def deleteLater(self):
        """Cleanup the handler on deletion."""
        self.removeHandler()
        super(LoggerQObjectMixin, self).deleteLater()

    def addLogs(self, loggers):
        """
        Add logger objects to the widget.

        Args:
            loggers (list[logging.Logger]|logging.Logger): Log object(s) to use.
        """
        loggers = ensure_iterable(loggers)
        for logger in loggers:
            if self.loggerHandler not in logger.handlers:
                logger.addHandler(self.loggerHandler)

    def removeLogs(self, loggers):
        """
        Remove logger objects from the widget.

        Args:
            loggers (list[logging.Logger]|logging.Logger): Log object(s) to use.
        """
        loggers = ensure_iterable(loggers)
        for logger in loggers:
            if self.loggerHandler in logger.handlers:
                logger.removeHandler(self.loggerHandler)

    def removeHandler(self):
        """Remove the handler from all known loggers."""
        for name in logging.root.manager.loggerDict:
            self.removeLogs(logging.getLogger(name))


class QLogPlainTextEdit(LoggerQObjectMixin, qt.QPlainTextEdit):
    """
    QPlainTextEdit to display messages received from assigned log objects.

    .. code-block:: python

        >>> import logging
        >>> from agora.core import qtui
        >>> logging.basicConfig(level=logging.DEBUG)
        >>> with qtui.qapp():
        ...     widget = qtui.QLogPlainTextEdit(log=[logging.getLogger('')])
        ...     widget.show()
        ...     logging.debug('debug')
        ...     logging.info('info')
        ...     logging.warning('warning')
        ...     logging.error('error')

    """

    def __init__(self, *args, **kwargs):
        self._levels = set()
        super(QLogPlainTextEdit, self).__init__(*args, **kwargs)

        self.setReadOnly(True)
        self.setLineWrapMode(qt.QPlainTextEdit.NoWrap)
        self.logRecordReceived.connect(SafeLogSlotConnect(self.appendLogRecord))

    @property
    def hasWarnings(self):
        return logging.WARNING in self._levels

    def clear(self):
        super(QLogPlainTextEdit, self).clear()
        self._levels.clear()

    @qt.Slot()
    def appendLogRecord(self, record):
        colors = self._recordColorMapping or COLORS
        color = colors[record.levelno].name()
        html = [
            '<font color="{}">'.format(color),
            '<pre>',
            self.loggerHandler.format(record),
            '</pre>',
            '</font>',
        ]
        self.appendHtml(''.join(html))
        self._levels.add(record.levelno)
