"""The UI for the attribute swapping."""

from functools import partial

from agora_community.vendor import mayax as mx
from agora_community import qtui

from .. import core
from . import main


def create_scene_locators_panel(state):
    # type: (main.MainState) -> qtui.QWidget
    """Create the UI for the attribute swapping."""
    with qtui.GroupVBox('Scene Locators', collapsed=True) as main_box:
        main_box.setToolTip('See the anim locators in the scene.')
        main_box.layout().setContentsMargins(
            4 * qtui.SCALE_FACTOR,
            4 * qtui.SCALE_FACTOR,
            4 * qtui.SCALE_FACTOR,
            4 * qtui.SCALE_FACTOR,
        )
        main_box.layout().setSpacing(2 * qtui.SCALE_FACTOR)

        qtui.addStyleClass(main_box, 'section')

        with qtui.QListWidget() as locators_list:
            locators_list.setSelectionMode(qtui.QAbstractItemView.ExtendedSelection)
            locators_list.itemSelectionChanged.connect(
                lambda: _on_locators_list_selection(locators_list)
            )

            selected_objects_callback = partial(_on_selected_objects_changed, locators_list)

            qtui.bind_callback(state, 'selected_objects_count', selected_objects_callback)
            main_box.destroyed.connect(
                lambda: qtui.unbind_callback(
                    state,
                    'selected_objects_count',
                    selected_objects_callback,
                )
            )

            _on_selected_objects_changed(locators_list)

    return main_box


@main.error_dialog
def _on_selected_objects_changed(locators_list_widget, _selected_objects_count=0):
    selected_objects = mx.cmd.ls(selection=True, type='transform')

    try:
        locators_list_widget.blockSignals(True)

        locators_list_widget.clear()

        for i, ctrl in enumerate(core.all_ctrls()):
            locators_list_widget.addItem(ctrl.uniqueName)

            if ctrl in selected_objects:
                locators_list_widget.setCurrentRow(i)
    finally:
        locators_list_widget.blockSignals(False)


@main.error_dialog
def _on_locators_list_selection(locators_list_widget):
    all_ctrls = core.all_ctrls()
    objects_to_select = []

    for item in locators_list_widget.selectedItems():
        index = locators_list_widget.row(item)

        objects_to_select.append(all_ctrls[index])

    mx.cmd.select(clear=True)

    if objects_to_select:
        mx.cmd.select(objects_to_select)
    else:
        mx.cmd.select(clear=True)
