import contextlib
import math

from maya import cmds, mel

from agora_community import mayalib

LIMB_CTRLS_ALIAS = {
    'hand_Fk': 'wrist_Fk',
    'hand_Fk_ctrl': 'wrist_Fk_ctrl',
    'hand_Ik': 'wrist_Ik',
    'handIk_ctrl': 'Ik_ctrl',
}

LIMBS_MATCHING = {
    'arm': {
        'root_ctrl': 'shoulder_Fk_ctrl',
        'ctrls': [
            'shoulder_Fk_ctrl',
            'elbow_Fk_ctrl',
            'hand_Fk_ctrl',
            'handIk_ctrl',
            'pv_ctrl',
            'settings_ctrl',
        ],
        'ctrls_fk': [
            'shoulder_Fk_ctrl',
            'elbow_Fk_ctrl',
            'hand_Fk_ctrl',
        ],
        'ctrls_ik': [
            'handIk_ctrl',
            'pv_ctrl',
        ],
        'ik_to_fk': [
            ('ikSwitch_offset', 'hand_Fk'),
            ('handIk_ctrl', 'ikSwitch'),
            ('pv_ctrl', 'elbow_Fk'),
        ],
        'fk_to_ik': [
            ('shoulder_Fk_ctrl', 'shoulder_Ik'),
            ('elbow_Fk_ctrl', 'elbow_Ik'),
            ('hand_Fk_ctrl', 'hand_Ik'),
        ],
    },
    'leg': {
        'root_ctrl': 'hip_Fk_ctrl',
        'ctrls': [
            'hip_Fk_ctrl',
            'knee_Fk_ctrl',
            'ankle_Fk_ctrl',
            'Ik_ctrl',
            'pv_ctrl',
            'settings_ctrl',
        ],
        'ctrls_fk': [
            'hip_Fk_ctrl',
            'knee_Fk_ctrl',
            'ankle_Fk_ctrl',
        ],
        'ctrls_ik': [
            'Ik_ctrl',
            'pv_ctrl',
        ],
        'ik_to_fk': [
            ('ikSwitch_offset', 'ankle_Fk'),
            ('Ik_ctrl', 'ikSwitch'),
            ('pv_ctrl', 'knee_Fk'),
        ],
        'fk_to_ik': [
            ('hip_Fk_ctrl', 'hip_Ik'),
            ('knee_Fk_ctrl', 'knee_Ik'),
            ('ankle_Fk_ctrl', 'ankle_Ik'),
        ],
    },
}


class ModeType:
    """The IK/FK match mode."""

    IK_TO_FK = 1
    FK_TO_IK = 2
    TOGGLE = 3
    NORMALIZE = 4


class RangeType:
    """The IK/FK match range."""

    CURRENT = 1
    TIMELINE = 2
    ALL = 3


class KeysType:
    """The IK/FK match keys."""

    SMART = 1
    BAKE = 2


@contextlib.contextmanager
def fast_viewport(suspend=True):
    """Disable viewport refreshing and change to DG evaluation."""
    if not suspend:
        yield
        return

    cmds.refresh(suspend=True)

    evaluation_mode = cmds.evaluationManager(query=True, mode=True)[0]

    if evaluation_mode != 'off':
        cmds.evaluationManager(mode='off')

    try:
        yield
    finally:
        if evaluation_mode != 'off':
            cmds.evaluationManager(mode=evaluation_mode)

        cmds.refresh(suspend=False)


@mayalib.undoable
def match(mode_type, range_type, keys_type):
    """Match IK/FK."""
    switches = get_kinematic_switches()

    if not switches:
        return 'No limbs selected.'

    match_data = []
    time_range = get_match_time_range(range_type)
    current_frame = cmds.currentTime(query=True)

    all_frames_to_key = set()
    all_objects_to_select = []
    all_missing_limb_objects = []

    for switch_attr in switches:
        limb_info = get_limb_info(switch_attr)

        if not limb_info:
            return 'Limb info not found.'

        missing_objects = get_limb_missing_objects(limb_info)

        if missing_objects:
            all_missing_limb_objects.extend(missing_objects)
            continue

        switch_attr_new_value = get_kinematic_switch_value(switch_attr, mode_type)

        if switch_attr_new_value == 0:
            objects_to_select = limb_info['ctrls_ik']
        else:
            objects_to_select = limb_info['ctrls_fk']

        if len(time_range) == 1:
            frames_to_key = [time_range[0]]
        elif keys_type == KeysType.SMART:
            frames_to_key = sorted(
                set(
                    get_frames_with_keys([switch_attr], time_range=time_range)
                    + get_frames_with_keys(limb_info['ctrls'], ['translate', 'rotate'], time_range)
                )
            )

            if not frames_to_key:
                frames_to_key = [current_frame]
        else:  # BAKE
            frames_to_key = get_time_range_frames(time_range)

        match_data.append((limb_info, switch_attr, switch_attr_new_value, frames_to_key))

        all_frames_to_key.update(frames_to_key)
        all_objects_to_select.extend(objects_to_select)

    all_frames_to_key = sorted(all_frames_to_key)

    if all_missing_limb_objects:
        return 'Missing limb objects:\n{}'.format('\n'.join(all_missing_limb_objects))

    with fast_viewport(len(all_frames_to_key) > 1):
        _match_create_safe_keys(match_data)

        # set keys on all frames to properly preserve the motion
        for frame in all_frames_to_key:
            with mayalib.undo_skip():
                cmds.currentTime(frame)

            for data in match_data:
                limb_info = data[0]
                cmds.setKeyframe(limb_info['ctrls'])

        # match
        for frame in all_frames_to_key:
            with mayalib.undo_skip():
                cmds.currentTime(frame)

            _match_switch_on_current_frame(frame, match_data)

        with mayalib.undo_skip():
            cmds.currentTime(current_frame)

    cmds.select(all_objects_to_select)

    cmds.filterCurve(all_objects_to_select, filter='euler')


def _match_create_safe_keys(match_data):
    for _limb_info, switch_attr, switch_attr_new_value, frames_to_key in match_data:
        if len(frames_to_key) < 2:
            continue

        prev_keyframe = get_previous_keyframe(switch_attr, frames_to_key[0])
        next_keyframe = get_next_keyframe(switch_attr, frames_to_key[-1])

        if prev_keyframe:
            prev_switch_value = get_kinematic_switch_value(switch_attr, time=prev_keyframe)

            if prev_switch_value != switch_attr_new_value:
                cmds.setKeyframe(switch_attr, value=prev_switch_value, time=frames_to_key[0] - 1)

        if next_keyframe:
            next_switch_value = get_kinematic_switch_value(switch_attr, time=next_keyframe)

            if next_switch_value != switch_attr_new_value:
                cmds.setKeyframe(switch_attr, value=next_switch_value, time=frames_to_key[-1] + 1)


def _match_switch_on_current_frame(frame, match_data):
    for limb_info, switch_attr, switch_attr_new_value, frames_to_key in match_data:
        if frame not in frames_to_key:
            continue

        switch_attr_value = get_kinematic_switch_value(switch_attr)

        if switch_attr_new_value == 0 and switch_attr_new_value != switch_attr_value:
            objects_to_match = limb_info['ik_to_fk']
        else:
            objects_to_match = limb_info['fk_to_ik']

        for source, target in objects_to_match:
            cmds.matchTransform(source, target)

        cmds.setAttr(switch_attr, switch_attr_new_value)

        cmds.setKeyframe(switch_attr)
        cmds.setKeyframe(limb_info['ctrls'], attribute=['translate', 'rotate'])


def get_limb_info(switch_attr):
    """Retrieve the limb info."""
    namespace = get_obj_namespace(switch_attr)
    module_name = get_module_name(switch_attr)

    limb_info = {}

    def get_obj_fullname(obj):
        obj_name = '{}{}_{}'.format(namespace, module_name, obj)

        if not cmds.objExists(obj_name) and obj in LIMB_CTRLS_ALIAS:
            obj_name = '{}{}_{}'.format(namespace, module_name, LIMB_CTRLS_ALIAS[obj])

        return obj_name

    for limb_type, limb_data in LIMBS_MATCHING.items():
        if cmds.objExists('{}{}_{}'.format(namespace, module_name, limb_data['root_ctrl'])):
            break
    else:
        return None

    for key, objects in LIMBS_MATCHING[limb_type].items():
        if isinstance(objects[0], tuple):
            limb_info[key] = [
                (
                    get_obj_fullname(obj1),
                    get_obj_fullname(obj2),
                )
                for obj1, obj2 in objects
            ]
        else:
            limb_info[key] = [get_obj_fullname(obj) for obj in objects]

    return limb_info


def get_limb_missing_objects(limb_info):
    """Retrieve the missing objects from the provided limb."""
    missing_objects = []

    for obj in limb_info['ctrls']:
        if not cmds.objExists(obj) and obj not in missing_objects:
            missing_objects.append(obj)

    for objects_to_match in [limb_info['ik_to_fk'], limb_info['fk_to_ik']]:
        for source_obj, target_obj in objects_to_match:
            if not cmds.objExists(source_obj) and source_obj not in missing_objects:
                missing_objects.append(source_obj)

            if not cmds.objExists(target_obj) and target_obj not in missing_objects:
                missing_objects.append(target_obj)

    return missing_objects


def get_kinematic_switches():
    """Retrieve the IK/FK switch attributes for the selected limbs."""
    selected_objects = cmds.ls(selection=True, transforms=True)
    switches = []

    for obj in selected_objects:
        switch_attr = get_kinematic_switch_attr(obj)

        if switch_attr and switch_attr not in switches:
            switches.append(switch_attr)

    return switches


def get_kinematic_switch_attr(ctrl):
    """Retrieve the IK/FK switch attribute."""
    switch_attr = '{}{}_settings_ctrl.IK_FK_switch'.format(
        get_obj_namespace(ctrl),
        get_module_name(ctrl),
    )

    if not cmds.objExists(switch_attr):
        return None

    return switch_attr


def get_kinematic_switch_value(switch_attr, mode_type=None, time=None):
    """Retrieve the IK/FK switch value for the selected mode type."""
    attr_args = {}

    if time is not None:
        attr_args['time'] = time

    if mode_type is None:
        return int(round(cmds.getAttr(switch_attr, **attr_args)))

    if mode_type == ModeType.FK_TO_IK:
        return 0

    if mode_type == ModeType.IK_TO_FK:
        return 1

    if mode_type == ModeType.NORMALIZE:
        return int(round(cmds.getAttr(switch_attr, **attr_args)))

    return int(not round(cmds.getAttr(switch_attr, **attr_args)))  # toggle


def get_selected_limbs_count():
    """Retrieve how many limbs are selected."""
    return len(get_kinematic_switches())


def get_match_time_range(range_type):
    """Retrieve the time range based on the provided range type."""
    if range_type == RangeType.CURRENT:
        return (cmds.currentTime(query=True),)

    selected_time_range = get_selected_time_range()

    if selected_time_range:
        return selected_time_range

    if range_type == RangeType.TIMELINE:
        return get_playback_range()

    return get_animation_range()


def get_module_name(ctrl):
    """Retrieve the module name from a rig control."""
    ctrl_name_parts = get_obj_name(ctrl).split('_')

    if ctrl_name_parts[0] in ('L', 'R'):
        return '{}_{}'.format(ctrl_name_parts[0], ctrl_name_parts[1])

    return ctrl_name_parts[0]


def get_module_base_name(ctrl):
    """Retrieve the module base name (without side) from a rig control."""
    ctrl_name_parts = get_obj_name(ctrl).split('_')

    if ctrl_name_parts[0] in ('L', 'R'):
        return ctrl_name_parts[1]

    return ctrl_name_parts[0]


def get_obj_name(obj):
    """Retrieve the name of an object."""
    if not obj:
        return None

    return obj.split(':')[-1].split('|')[-1]


def get_obj_namespace(obj):
    """Retrieve the namespace of an object."""
    namespace = obj.rpartition(':')[0]

    if namespace:
        return namespace + ':'

    return ''


def get_animation_range():
    """Retrieve the animation's time range."""
    return (
        cmds.playbackOptions(query=True, animationStartTime=True),
        cmds.playbackOptions(query=True, animationEndTime=True),
    )


def get_playback_range():
    """Retrieve the playback's time range."""
    return (
        cmds.playbackOptions(query=True, minTime=True),
        cmds.playbackOptions(query=True, maxTime=True),
    )


def get_selected_time_range():
    """Get the selected time range from the global time control."""
    time_control_name = mel.eval('$tmpVar=$gPlayBackSlider')

    if cmds.timeControl(time_control_name, query=True, rangeVisible=True):
        return tuple(cmds.timeControl(time_control_name, query=True, rangeArray=True))

    return ()


def get_time_range_frames(time_range):
    """Retrieve all the frames between a time range."""
    return list(
        range(
            int(math.floor(time_range[0])),
            int(math.ceil(time_range[1])) + 1,
        )
    )


def get_frames_with_keys(objects, attributes=(), time_range=()):
    """Get all the frames that have keys for the specified attributes."""
    frames = []

    for obj in objects:
        if '.' in obj:
            obj, obj_attr = obj.split('.')

            if not attributes:
                attributes = (obj_attr,)

        for attr_name in attributes:
            attr_fullname = '{}.{}'.format(obj, attr_name)

            for frame in cmds.keyframe(attr_fullname, query=True, time=time_range) or []:
                if frame not in frames:
                    frames.append(frame)

    frames.sort()

    return frames


def get_previous_keyframe(obj, reference_frame):
    """Retrieve the previous keyframe of an object."""
    keyframe = cmds.findKeyframe(obj, which='previous', time=(reference_frame,))

    if keyframe < reference_frame:
        return keyframe

    return None


def get_next_keyframe(obj, reference_frame):
    """Retrieve the next keyframe of an object."""
    keyframe = cmds.findKeyframe(obj, which='next', time=(reference_frame,))

    if keyframe > reference_frame:
        return keyframe

    return None
