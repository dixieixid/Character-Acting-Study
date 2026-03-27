"""Tool to pan and zoom the camera."""

import functools

from agora_community import qtui, mayaui

from . import core
from .constants import *


def launch():
    """Launch the Pan Zoom tool."""
    LOGGER.info(f'Launching {TOOL_TITLE}...')

    PanZoomWindow(parent=mayaui.mayaMainWindow()).show()


def error_dialog(func):
    """Catch errors from decorated functions and display them in a dialog."""

    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except core.PanZoomError as error:
            qtui.QMessageBox.warning(mayaui.mayaMainWindow(), 'Pan Zoom Warning', str(error))
        except Exception as error:
            error_msg = (
                'An <b>error</b> occurred:'
                '<br><b style="color: #f87f7f">{}: <i>{}</i></b>'
                '<br><br>Check the <b>Script Editor</b> for more details.'.format(
                    type(error).__name__,
                    error,
                )
            )

            qtui.QMessageBox.critical(mayaui.mayaMainWindow(), 'Pan Zoom Error', error_msg)

            raise error

    return func_wrapper


class MainState(qtui.BindableData):
    """The UI main state."""

    panzoom_enabled = False

    tracking_enabled = False
    tracking_info = ''

    zoom = 1.0


@mayaui.dockableWindow(launcher=launch, initialWidth=250, initialHeight=75)
class PanZoomWindow(qtui.ToolWindow):
    """Main window for the Pan Zoom tool."""

    def __init__(self, parent=None):
        super(PanZoomWindow, self).__init__(TOOL_TITLE, parent)

        mayaui.addBaseStyleSheet(self)
        qtui.addStyleSheet(self, TOOL_STYLE_PATH)

        self.state = MainState(tracking_enabled=core.is_tracking_enabled())

        self._update_status_info()
        self._create_ui()

    def _create_ui(self):
        """Create the UI."""
        state = self.state

        with self.layout() as main_layout:
            main_layout.setContentsMargins(0, 0, 0, 0)

            with qtui.QVBoxLayout() as layout:
                layout.setContentsMargins(
                    4 * qtui.SCALE_FACTOR,
                    4 * qtui.SCALE_FACTOR,
                    4 * qtui.SCALE_FACTOR,
                    0,
                )

                with qtui.Slider(0.001, 1.0) as zoom_slider:
                    qtui.bind(zoom_slider, state, 'zoom')
                    zoom_slider.valueChanged.connect(self._on_zoom_changed)

                with qtui.QHBoxLayout() as layout:
                    layout.setSpacing(4 * qtui.SCALE_FACTOR)

                    with qtui.QPushButton('Track') as track_btn:
                        track_btn.setSizePolicy(
                            qtui.QSizePolicy.Minimum, qtui.QSizePolicy.Expanding
                        )
                        track_btn.clicked.connect(self._on_track)
                        qtui.bind_invisibility(track_btn, self.state, 'tracking_enabled')

                    with qtui.QPushButton('Untrack') as untrack_btn:
                        untrack_btn.setSizePolicy(
                            qtui.QSizePolicy.Minimum, qtui.QSizePolicy.Expanding
                        )
                        untrack_btn.clicked.connect(self._on_untrack)
                        qtui.bind_visibility(untrack_btn, self.state, 'tracking_enabled')
                        qtui.addStyleClass(untrack_btn, 'button--enabled')

                    with qtui.QPushButton('Frame') as frame_btn:
                        frame_btn.setSizePolicy(
                            qtui.QSizePolicy.Minimum, qtui.QSizePolicy.Expanding
                        )
                        frame_btn.clicked.connect(self._on_frame)
                        qtui.bind_activation(
                            frame_btn,
                            state,
                            'tracking_enabled',
                            display_processor=lambda value: not value,
                        )

                    with qtui.QPushButton() as panzoom_btn:
                        panzoom_btn.setIcon(qtui.QPixmap(':PanZoom').scaled(24, 24))
                        panzoom_btn.setSizePolicy(
                            qtui.QSizePolicy.Minimum, qtui.QSizePolicy.Expanding
                        )
                        panzoom_btn.clicked.connect(self._on_panzoom)

                        self._panzoom_btn = panzoom_btn
                        self._update_panzoom_btn()

                    layout.setStretchFactor(track_btn, 1)
                    layout.setStretchFactor(untrack_btn, 1)

            with qtui.QLabel() as status_info:
                qtui.bind(status_info, state, 'tracking_info')
                qtui.addStyleClass(status_info, 'tracking-info')

    @error_dialog
    def _on_track(self):
        core.track_objects(zoom=self.state.zoom)

        self.state.tracking_enabled = True

        self._update_panzoom_btn()
        self._update_status_info()

    @error_dialog
    def _on_untrack(self):
        core.untrack()

        self.state.tracking_enabled = False

        self._update_panzoom_btn()
        self._update_status_info()

    @error_dialog
    def _on_frame(self):
        core.frame_objects(zoom=self.state.zoom)

        self._update_panzoom_btn()

    @error_dialog
    def _on_zoom_changed(self, zoom_value):
        core.update_zoom(zoom_value)

        self._update_panzoom_btn()

    @error_dialog
    def _on_panzoom(self):
        core.toggle_panzoom()

        self._update_panzoom_btn()

    @error_dialog
    def _update_status_info(self):
        tracked_camera = core.get_tracked_camera()
        tracked_objects = core.get_tracked_objects()

        if tracked_camera:
            self.state.tracking_info = '<b>{}</b> | {}{}'.format(
                tracked_camera.name,
                tracked_objects[0],
                ' ... (+{})'.format(len(tracked_objects) - 1) if len(tracked_objects) > 1 else '',
            )
        else:
            self.state.tracking_info = 'Nothing tracked.'

    @error_dialog
    def _update_panzoom_btn(self):
        if core.is_panzoom_enabled():
            qtui.addStyleClass(self._panzoom_btn, 'button--enabled')
        else:
            qtui.removeStyleClass(self._panzoom_btn, 'button--enabled')
