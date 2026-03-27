"""Tool to make it easier to work with image planes."""

from functools import partial, wraps
import os
import contextlib

from maya import cmds
from maya.api import OpenMaya as om

from agora_community import qtui, lib, mayaui

from . import core, utils
from .constants import *


_FREE_LABEL = '---'


def launch():
    """Launch the Image Plane tool."""
    LOGGER.info(f'Launching {TOOL_TITLE}...')

    ImagePlaneWindow(parent=mayaui.mayaMainWindow()).show()


def error_dialog(func):
    """Catch errors from decorated functions and display them in a dialog."""

    @wraps(func)
    def func_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except core.ImagePlaneError as error:
            qtui.QMessageBox.warning(mayaui.mayaMainWindow(), 'Image Plane Warning', str(error))
        except Exception as error:
            error_msg = (
                'An <b>error</b> occurred:'
                '<br><b style="color: #f87f7f">{}: <i>{}</i></b>'
                '<br><br>Check the <b>Script Editor</b> for more details.'.format(
                    type(error).__name__,
                    error,
                )
            )

            qtui.QMessageBox.critical(mayaui.mayaMainWindow(), 'Image Plane Error', error_msg)

            raise error

    return func_wrapper


class MainState(qtui.BindableData):
    """The UI main state."""

    class ImagePlaneProperties(qtui.BindableData):
        node = None
        camera_name = ''
        frame_start = 0
        frame_offset = 0
        depth = 0
        opacity = 1.0
        visible_in_all_views = False
        selectable = False
        time_remap = False

    image_planes = []
    cameras = []

    selected_image_plane = ImagePlaneProperties()
    selected_image_plane_index = -1

    refreshing = False
    refreshing_properties = False
    obj_selection_in_progress = False

    busy = False

    def __init__(self, **attributes):
        super(MainState, self).__init__(**attributes)

        self._obj_selection_callback_id = om.MEventMessage.addEventCallback(
            'SelectionChanged',
            lib.weak_method_proxy(self._on_obj_selection),
        )

        self.refresh()

    def __del__(self):
        self.remove_callbacks()

    def remove_callbacks(self):
        if self._obj_selection_callback_id:
            om.MEventMessage.removeCallback(self._obj_selection_callback_id)
            self._obj_selection_callback_id = 0

    def refresh(self):
        """Gather all the data."""
        try:
            self.refreshing = True

            self.selected_image_plane_index = -1

            self.image_planes = core.get_image_planes_info()
            self.cameras = [''] + utils.get_all_cameras()

            selected_objects = cmds.ls(selection=True, type='transform')

            for i, image_plane_info in enumerate(self.image_planes):
                if image_plane_info['node'] in selected_objects:
                    self.selected_image_plane_index = i
                    break

            self.refresh_image_plane_properties()
        finally:
            self.refreshing = False

    def refresh_image_plane_properties(self):
        """Update the properties for the selected image plane."""
        if self.selected_image_plane_index == -1:
            return

        selected_info = self.image_planes[self.selected_image_plane_index]

        try:
            self.refreshing_properties = True

            for attr_name in self.selected_image_plane:
                self.selected_image_plane[attr_name] = selected_info[attr_name]
        finally:
            self.refreshing_properties = False

    @contextlib.contextmanager
    def init_busy(self):
        """Put the UI in busy mode."""
        self.busy = True

        qtui.QCoreApplication.instance().processEvents(qtui.QEventLoop.AllEvents, 1)

        try:
            yield
        finally:
            self.busy = False

    def _on_obj_selection(self, *_):
        try:
            self.obj_selection_in_progress = True

            self.refresh()
        finally:
            self.obj_selection_in_progress = False


@mayaui.dockableWindow(launcher=launch, initialWidth=250, initialHeight=75)
class ImagePlaneWindow(qtui.ToolWindow):
    """Main window for the Image Plane tool."""

    def __init__(self, parent=None):
        super(ImagePlaneWindow, self).__init__(TOOL_TITLE, parent)

        mayaui.addBaseStyleSheet(self)
        qtui.addStyleSheet(self, TOOL_STYLE_PATH)

        self.state = MainState()

        self._busy_overlay = qtui.BusyOverlay(self)

        self._create_ui()

    def onMenuBar(self, menu_bar):
        with self.menuBarLayout():
            with qtui.IconButton('eye') as btn:
                btn.clicked.connect(self._on_show_image_plane)

            with qtui.IconButton('eye-slash') as btn:
                btn.clicked.connect(self._on_hide_image_plane)

            with qtui.IconButton('plus') as btn:
                btn.clicked.connect(self._on_add_image_plane)

    def onClose(self):
        self.state.remove_callbacks()

    def _create_ui(self):
        """Create the UI."""
        qtui.bind_visibility(self._busy_overlay, self.state, 'busy')

        with self.layout():
            self._create_image_planes_list()
            self._create_image_plane_properties()

    def _create_image_planes_list(self):
        state = self.state

        with qtui.QListWidget() as images_list:
            images_list.setAlternatingRowColors(True)
            images_list.setMinimumHeight(50 * qtui.SCALE_FACTOR)

            qtui.bind(
                images_list,
                state.image_planes,
                self._create_image_plane_list_item,
            )
            qtui.bind(images_list, state, 'selected_image_plane_index')
            qtui.bind_callback(
                state,
                'selected_image_plane_index',
                lib.weak_method_proxy(self._on_image_planes_list_selection),
            )

    def _create_image_plane_list_item(self, item, _index, _data):
        img_plane_name = item['node'].name
        img_plane_camera_name = item['camera_name'] if item['camera_name'] else _FREE_LABEL

        with qtui.QWidget() as widget:
            if not item['visible']:
                qtui.addStyleClass(widget, 'image-plane-item--hidden')

            with qtui.QHBoxLayout() as layout:
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(0)

                with qtui.QVBoxLayout() as layout:
                    layout.setContentsMargins(
                        2 * qtui.SCALE_FACTOR,
                        2 * qtui.SCALE_FACTOR,
                        2 * qtui.SCALE_FACTOR,
                        2 * qtui.SCALE_FACTOR,
                    )

                    with qtui.QLabel(img_plane_name) as label:
                        qtui.addStyleClass(label, 'image-plane-item__image-label')

                    with qtui.QLabel(img_plane_camera_name) as label:
                        qtui.addStyleClass(label, 'image-plane-item__camera-label')

                with qtui.QVBoxLayout() as layout:
                    with qtui.IconButton('eye' if item['visible'] else 'eye-slash') as btn:
                        if item['visible']:
                            btn.clicked.connect(partial(self._on_hide_image_plane, item))
                        else:
                            btn.clicked.connect(partial(self._on_show_image_plane, item))

                        btn.setFixedHeight(16 * qtui.SCALE_FACTOR)
                        qtui.addStyleClass(btn, 'image-plane-item__action-button')

                    with qtui.IconButton('minus') as btn:
                        btn.clicked.connect(partial(self._on_delete_image_plane, item))
                        btn.setFixedHeight(16 * qtui.SCALE_FACTOR)
                        qtui.addStyleClass(btn, 'image-plane-item__action-button')

        return widget

    def _create_image_plane_properties(self):
        selected_image_plane = self.state.selected_image_plane
        on_property_changed_fn = lib.weak_method_proxy(self._on_image_plane_property_changed)

        with qtui.QWidget() as widget:
            qtui.bind_activation(
                widget,
                self.state,
                'selected_image_plane_index',
                display_processor=lambda index: index != -1,
            )

            with qtui.QFormLayout() as form:
                form.setContentsMargins(0, 4 * qtui.SCALE_FACTOR, 0, 0)

                with qtui.QHBoxLayout() as layout:
                    with qtui.QComboBox() as combobox:
                        combobox.setSizePolicy(qtui.QSizePolicy.Expanding, qtui.QSizePolicy.Minimum)
                        qtui.bind(
                            combobox,
                            self.state.cameras,
                            lambda item, *_args: item if item else _FREE_LABEL,
                        )
                        qtui.bind(
                            combobox,
                            self.state.selected_image_plane,
                            'camera_name',
                            display_processor=lambda value: value if value else _FREE_LABEL,
                            value_processor=lambda value: '' if value == _FREE_LABEL else value,
                        )
                        qtui.bind_callback(
                            selected_image_plane,
                            'camera_name',
                            partial(on_property_changed_fn, 'camera_name'),
                        )

                    with qtui.IconButton('mouse-pointer') as btn:
                        btn.clicked.connect(self._on_select_camera)
                        qtui.addStyleClass(btn, 'form__icon-button')

                    form.addRow('Camera', layout)

                with qtui.QHBoxLayout() as layout:
                    with qtui.QLineEdit() as field:
                        field.setValidator(qtui.QIntValidator())
                        qtui.bind(field, selected_image_plane, 'frame_start')
                        qtui.bind_callback(
                            selected_image_plane,
                            'frame_start',
                            partial(on_property_changed_fn, 'frame_start'),
                        )

                    with qtui.QLabel('Offset'):
                        pass

                    with qtui.QLineEdit() as field:
                        field.setValidator(qtui.QIntValidator())
                        qtui.bind(field, selected_image_plane, 'frame_offset')
                        qtui.bind_callback(
                            selected_image_plane,
                            'frame_offset',
                            partial(on_property_changed_fn, 'frame_offset'),
                        )

                    form.addRow('Frame Start', layout)

                with qtui.QLineEdit() as field:
                    field.setValidator(qtui.QDoubleValidator())
                    form.addRow('Depth', field)
                    qtui.bind(field, selected_image_plane, 'depth')
                    qtui.bind_callback(
                        selected_image_plane,
                        'depth',
                        partial(on_property_changed_fn, 'depth'),
                    )

                with qtui.Slider(0.0, 1.0) as field:
                    field.setValue(1.0)
                    form.addRow('Opacity', field)
                    qtui.bind(field, selected_image_plane, 'opacity')
                    qtui.bind_callback(
                        selected_image_plane,
                        'opacity',
                        partial(on_property_changed_fn, 'opacity'),
                    )

                with qtui.QHBoxLayout() as layout:
                    layout.setSpacing(6 * qtui.SCALE_FACTOR)

                    with qtui.QCheckBox('Enabled') as field:
                        qtui.bind(field, selected_image_plane, 'time_remap')
                        qtui.bind_callback(
                            selected_image_plane,
                            'time_remap',
                            partial(on_property_changed_fn, 'time_remap'),
                        )

                    with qtui.QPushButton('Curve') as btn:
                        btn.clicked.connect(self._on_select_image_plane_curve)
                        btn.setSizePolicy(qtui.QSizePolicy.Expanding, qtui.QSizePolicy.Minimum)
                        qtui.addStyleClass(btn, 'form__inline-button')
                        qtui.bind_activation(btn, selected_image_plane, 'time_remap')

                    form.addRow('Time Remap', layout)

                with qtui.QHBoxLayout() as layout:
                    layout.setSpacing(6 * qtui.SCALE_FACTOR)
                    form.addRow('', layout)

                    with qtui.QPushButton('Fit to Resolution Gate') as btn:
                        btn.clicked.connect(self._on_request_fit_to_resolution_gate)
                    with qtui.QPushButton('Fit to Film Gate') as btn:
                        btn.clicked.connect(self._on_request_fit_to_film_gate)

                form.addRow('', qtui.LayoutSeparator())

                with qtui.QCheckBox('Visible in all views') as field:
                    form.addRow('', field)
                    qtui.bind(field, selected_image_plane, 'visible_in_all_views')
                    qtui.bind_activation(field, selected_image_plane, 'camera_name')
                    qtui.bind_callback(
                        selected_image_plane,
                        'visible_in_all_views',
                        partial(on_property_changed_fn, 'visible_in_all_views'),
                    )

                with qtui.QCheckBox('Selectable in viewport') as field:
                    form.addRow('', field)
                    qtui.bind(field, selected_image_plane, 'selectable')
                    qtui.bind_callback(
                        selected_image_plane,
                        'selectable',
                        partial(on_property_changed_fn, 'selectable'),
                    )

    @error_dialog
    def _on_image_planes_list_selection(self, index):
        if not self.state.obj_selection_in_progress and index != -1:
            core.select_image_plane(self.state.image_planes[index].node)

    @error_dialog
    def _on_add_image_plane(self):
        starting_directory = next(
            filter(
                lambda x: x and os.path.exists(x),
                map(str.strip, os.getenv('AGORA_IMAGE_PLANE_BROWSE_PATH', '').split(';')),
            ),
            '',
        )
        file_path = cmds.fileDialog2(
            fileMode=1,
            caption='Select an image or video file',
            fileFilter='Image/Video Files ({});;All Files (*.*)'.format(
                ' '.join('*' + ext for ext in SUPPORTED_FILE_EXTS)
            ),
            startingDirectory=starting_directory,
        )
        if not file_path:
            return

        file_path = file_path[0]
        supported_video_exts = {'.mov', '.avi'}
        if (
            utils.is_video_file(file_path)
            and os.path.splitext(file_path)[-1].lower() not in supported_video_exts
        ):
            qtui.warningDialog(
                'Unsupported Video File',
                'The selected <b>video format</b> is <b>not supported</b>.',
                mayaui.mayaMainWindow(),
            )
            return

        core.add_image_plane(file_path)

        self.state.refresh()

    @error_dialog
    def _on_delete_image_plane(self, item):
        core.delete_image_plane(item['node'])

        self.state.refresh()

    @error_dialog
    def _on_show_image_plane(self, item=None):
        core.show_image_plane(item['node'] if item else None)

        self.state.refresh()

    @error_dialog
    def _on_hide_image_plane(self, item=None):
        core.hide_image_plane(item['node'] if item else None)

        self.state.refresh()

    @error_dialog
    def _on_select_image_plane_curve(self):
        core.select_image_plane_frame_curve(self.state.selected_image_plane.node)

    @error_dialog
    def _on_request_fit_to_resolution_gate(self):
        core.fit_image_plane_to_resolution_gate(self.state.selected_image_plane.node.name)

    @error_dialog
    def _on_request_fit_to_film_gate(self):
        core.fit_image_plane_to_film_gate(self.state.selected_image_plane.node.name)

    @error_dialog
    def _on_image_plane_property_changed(self, name, value):
        if not self.state.refreshing and not self.state.refreshing_properties:
            core.update_image_plane_property(self.state.selected_image_plane.node, name, value)

            if name == 'camera_name':
                self.state.refresh()

    @error_dialog
    def _on_select_camera(self):
        core.select_image_plane_camera(self.state.selected_image_plane.node)
