"""IK/FK Match Tool."""

from maya.api import OpenMaya as om

from agora_community import qtui, lib, mayaui

from . import core
from .constants import *


def launch():
    """Open the main UI window."""
    MainWindow(parent=mayaui.mayaMainWindow()).show()


@mayaui.dockableWindow(launcher=launch, initialWidth=250, initialHeight=100)
class MainWindow(qtui.ToolWindow):
    """All the functionality will be accessible through this UI."""

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(TOOL_TITLE, parent)

        mayaui.addBaseStyleSheet(self)
        qtui.addStyleSheet(self, TOOL_STYLE_PATH)

        self._create_ui()
        self._add_callbacks()
        self._update_info()
        self._update_match_button()

    def onClose(self):
        """Cleanup on close."""
        self._remove_callbacks()

    def _create_ui(self):
        self.mode_btn = qtui.ToggleButton()
        self.mode_btn.addState('IK > FK', core.ModeType.IK_TO_FK)
        self.mode_btn.addState('FK > IK', core.ModeType.FK_TO_IK)
        self.mode_btn.addState('Toggle', core.ModeType.TOGGLE)
        self.mode_btn.addState('Normalize', core.ModeType.NORMALIZE)
        self.mode_btn.setState(core.ModeType.TOGGLE)
        qtui.addStyleClass(self.mode_btn, 'mode-toggle')

        self.range_btn = qtui.ToggleButton()
        self.range_btn.addState('Current', core.RangeType.CURRENT)
        self.range_btn.addState('Timeline', core.RangeType.TIMELINE)
        self.range_btn.addState('All', core.RangeType.ALL)
        self.range_btn.setState(core.RangeType.TIMELINE)
        self.range_btn.stateChanged.connect(self._on_range_changed)
        qtui.addStyleClass(self.range_btn, 'range-toggle')

        self.keys_btn = qtui.ToggleButton()
        self.keys_btn.addState('Smart', core.KeysType.SMART)
        self.keys_btn.addState('Bake', core.KeysType.BAKE)
        self.keys_btn.setState(core.KeysType.SMART)
        qtui.addStyleClass(self.keys_btn, 'keys-toggle')

        self.mode_btn.setSizePolicy(qtui.QSizePolicy.Expanding, qtui.QSizePolicy.Minimum)
        self.range_btn.setSizePolicy(qtui.QSizePolicy.Expanding, qtui.QSizePolicy.Minimum)
        self.keys_btn.setSizePolicy(qtui.QSizePolicy.Expanding, qtui.QSizePolicy.Minimum)

        self.match_btn = qtui.QPushButton('Match')
        self.match_btn.clicked.connect(self._on_match)

        self.range_info_label = qtui.QLabel()
        self.limbs_info_label = qtui.QLabel()
        self.range_info_label.setSizePolicy(qtui.QSizePolicy.Expanding, qtui.QSizePolicy.Minimum)
        self.limbs_info_label.setSizePolicy(qtui.QSizePolicy.Expanding, qtui.QSizePolicy.Minimum)
        qtui.addStyleClass(self.range_info_label, 'info-label')
        qtui.addStyleClass(self.limbs_info_label, 'info-label')

        form_layout = qtui.QFormLayout()

        form_layout.addRow('Mode', self.mode_btn)
        form_layout.addRow('Range', self.range_btn)
        form_layout.addRow('Keys', self.keys_btn)

        info_layout = qtui.QHBoxLayout()
        info_layout.addWidget(qtui.QLabel('Range:'))
        info_layout.addWidget(self.range_info_label)
        info_layout.addWidget(qtui.QLabel('Selected Limbs:'))
        info_layout.addWidget(self.limbs_info_label)

        self.layout().addLayout(form_layout)
        self.layout().addWidget(qtui.LayoutSeparator())
        self.layout().addLayout(info_layout)
        self.layout().addWidget(qtui.LayoutSeparator())
        self.layout().addWidget(self.match_btn)

    def _add_callbacks(self):
        self._maya_callbacks = [
            om.MEventMessage.addEventCallback(
                'SelectionChanged',
                lib.weak_method_proxy(self._on_obj_selection),
            ),
            om.MEventMessage.addEventCallback(
                'timeChanged',
                lib.weak_method_proxy(self._on_time_changed),
            ),
            om.MEventMessage.addEventCallback(
                'playbackRangeChanged',
                lib.weak_method_proxy(self._on_time_changed),
            ),
            om.MEventMessage.addEventCallback(
                'playbackRangeSliderChanged',
                lib.weak_method_proxy(self._on_time_changed),
            ),
        ]

    def _remove_callbacks(self):
        for callback_id in self._maya_callbacks:
            om.MEventMessage.removeCallback(callback_id)

    def _on_match(self):
        match_result = core.match(
            mode_type=self.mode_btn.state(),
            range_type=self.range_btn.state(),
            keys_type=self.keys_btn.state(),
        )

        if match_result:
            qtui.QMessageBox.warning(self, 'IK/FK Match Warning', match_result)

    def _on_range_changed(self, state):
        if state == core.RangeType.CURRENT:
            self.keys_btn.setDisabled(True)
        else:
            self.keys_btn.setEnabled(True)

        self._update_info()

    def _on_obj_selection(self, *_):
        self._update_info()
        self._update_match_button()

    def _on_time_changed(self, *_):
        self._update_info()

    def _update_match_button(self):
        if core.get_selected_limbs_count():
            self.match_btn.setEnabled(True)
        else:
            self.match_btn.setDisabled(True)

    def _update_info(self):
        time_range = core.get_match_time_range(self.range_btn.state())
        selected_limbs_count = core.get_selected_limbs_count()

        range_info = ' - '.join(str(time).rstrip('0').rstrip('.') for time in time_range)
        limbs_info = str(selected_limbs_count)

        self.range_info_label.setText(range_info)
        self.limbs_info_label.setText(limbs_info)
