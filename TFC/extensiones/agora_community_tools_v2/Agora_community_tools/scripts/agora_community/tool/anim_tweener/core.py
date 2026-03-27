import maya.cmds as cmds
import maya.mel as mel

from .constants import *


def get_mods():
    """return what keys between Ctrl, Alt, and Shift are held while dragging the slider
    0 = Normal
    1 = Shift
    4 = Ctrl
    9 = Alt + Shift
    """
    mod = int(cmds.getModifiers())
    return mod


def tm_tweener_drag(graph_keys_rules, tween_value, graph_sel, mod):
    """actions called while slider is being dragged
    graph_keys_rules: Dictionary of dictionary containing all the info of value target if slider were slided -100 or 100
        
        each sub-dictionnaries are:
                pre target [0]
                modified att [1]
                curVal [2]
                post target [3]
                attribute [4]
        
        formating will be different if it's a graph selection or not:
            graph_sel is ON: [0.0, 20.0, 36.99110846179831, 52.17910349087019, 'pCylinder1_rotateZ']
            graph_sel is OFF: {'pCylinder1.translateX': [0.0, 4.5423526971051755, 4.67566689261858]}
        
    tween_value: value between -100 and 100 of the slider
    graph_sel: boolean wether the tool should act on graph editor selection or not
    mod: a number code to tell wether Ctrl, Shift, or alt are held
    """
    if not len(cmds.ls(selection=True)) == 0:
        if graph_sel is None:
            for rule in graph_keys_rules:
                x = graph_keys_rules[rule][1]
                if tween_value < 0:
                    y = graph_keys_rules[rule][0]
                else:
                    y = graph_keys_rules[rule][2]

                if x > y:
                    plage = -(abs(x - y))
                else:
                    plage = (abs(x - y))
                cmds.setAttr(rule, ((abs(tween_value) / 100.0 * plage + x)))

        else:

            for rule in graph_keys_rules:
                x = rule[2]
                if tween_value < 0:
                    y = rule[0]
                else:
                    y = rule[3]

                if x > y:
                    plage = - (abs(x - y))
                else:
                    plage = (abs(x - y))
                cmds.keyframe(rule[4], edit=True, vc=((abs(tween_value) / 100.0 * plage + x)), t=(rule[1], rule[1]))


def get_aniattr():
    """
    Called to query channels to tween according to timeslider selection
    """
    ani_attr = []
    g_play_back_slider = mel.eval('$temp=$gPlayBackSlider')

    range_array = cmds.timeControl(g_play_back_slider, q=1, rangeArray=1)

    if is_timeline_sel():
        selected_attrs = cmds.channelBox("mainChannelBox", q=1, sma=1)
        graph_sel = cmds.keyframe(query=True, selected=True, name=True)
        if selected_attrs is not None and graph_sel is None:

            raw_animatable_filter = cmds.listAnimatable()
            animatable_filter = []

            for atts in raw_animatable_filter:
                animatable_filter.append(atts[1:].split("|")[-1:][0])

            for attShortname in selected_attrs:
                for object in cmds.ls(selection=True):
                    attr = object + '.' + cmds.listAttr("{0}.{1}".format(object, attShortname))[0]

                    if attr in animatable_filter:
                        ani_attr.append(attr)
        else:
            for object in cmds.ls(selection=True):
                attr = cmds.listAnimatable(object)
                for att in attr:
                    channel = att.split('|')[-1:]
                    if cmds.listConnections(channel, p=True, type='animCurve') or cmds.listConnections(channel, p=True,
                                                                                                       type='animLayer'):
                        ani_attr.append(channel)

        cmds.selectKey(clear=True)

        for item in ani_attr:
            cmds.selectKey(item, add=True, time=(range_array[0], range_array[1]))
    return ani_attr


def tmt_get_tween_goals(mod, ani_attr):
    """
    Long function simply to create a dictionary or list with directive for dragging.
    """
    if len(cmds.ls(selection=True)) == 0:
        return
    next_key = cmds.findKeyframe(which="next")
    cur_key = cmds.currentTime(query=True)
    prev_key = cmds.findKeyframe(which="previous")

    if mod not in SUPPORTED_MODS:
        mod = 0

    tween_vals = {}
    tween_vals.clear()

    tween_graph = 0
    graph_sel = cmds.keyframe(query=True, selected=True, name=True)
    if graph_sel is not None:
        tween_graph = 1

    selected_attrs = cmds.channelBox("mainChannelBox", q=1, sma=1)
    if selected_attrs is not None and tween_graph == 0:

        raw_animatable_filter = cmds.listAnimatable()
        animatable_filter = []

        for atts in raw_animatable_filter:
            animatable_filter.append(atts[1:].split("|")[-1:][0])

        for attShortname in selected_attrs:
            for object in cmds.ls(selection=True):
                attr = object + '.' + cmds.listAttr("{0}.{1}".format(object, attShortname))[0]

                if attr in animatable_filter:
                    ani_attr.append(attr)

    elif tween_graph == 0:
        for object in cmds.ls(selection=True):
            attr = cmds.listAnimatable(object) or []
            for att in attr:
                channel = att.split('|')[-1:]
                if cmds.listConnections(channel, p=True, type='animCurve') or cmds.listConnections(channel, p=True,
                                                                                                   type='animLayer'):
                    if mod == 4 and 'visibility' in channel[0]:
                        continue
                    ani_attr.append(channel[0])

    elif tween_graph == 1:
        for selcurve in graph_sel:
            ani_attr.append(selcurve)

    if tween_graph == 0:
        for attributes in ani_attr:
            valdict = []
            del valdict[:]
            if mod == 0:  # no modifier
                prev_val = cmds.getAttr(attributes, time=prev_key)
            if mod == 1:  # shift modifier
                prev_val = cmds.getAttr(attributes, time=prev_key) - (
                        (cmds.getAttr(attributes, time=prev_key) - cmds.getAttr(attributes, time=next_key)) /
                        (next_key - prev_key) * (cur_key - prev_key))
            if mod == 4:  # ctrl modifier
                prev_val = 0

            cur_val = cmds.getAttr(attributes, time=cur_key)

            if mod == 0:  # no modifier
                next_val = cmds.getAttr(attributes, time=next_key)
            if mod == 1:  # shift modifier
                median = cmds.getAttr(attributes, time=prev_key) - (
                        (cmds.getAttr(attributes, time=prev_key) - cmds.getAttr(attributes, time=next_key)) /
                        (next_key - prev_key) * (cur_key - prev_key))
                cur_val
                next_val = cur_val - median + cur_val
            if mod == 4:  # ctrl modifier
                if 'visibility' in attributes:
                    next_val = 1
                else:
                    next_val = cur_val * 2

            if mod == 9:
                # prev val should be the median value
                # next val should be current difference value between cur and median,  value X2
                prev_key_val = cmds.getAttr(attributes, time=prev_key)
                next_key_val = cmds.getAttr(attributes, time=next_key)

                prev_val = (prev_key_val - (prev_key_val - next_key_val) / (next_key - prev_key) * (cur_key - prev_key))

                median = prev_key_val - (prev_key_val - next_key_val) / (next_key - prev_key) * (cur_key - prev_key)
                next_val = (cur_val - median + cur_val)

            valdict = [float(prev_val), float(cur_val), float(next_val)]
            tween_vals[attributes] = valdict
        return tween_vals, None

    else:
        graph_keys_rules = []
        for curve in graph_sel:
            graph_sel_a = cmds.keyframe(curve, selected=True, query=True, tc=True)

            keys = cmds.keyframe(curve, query=True, timeChange=True)
            keys_tail = keys[:]
            chuncks = []
            grouped = []

            keys_tail.insert(0, keys[0])
            keys_tail.append(keys[-1])

            index = 0
            for number in keys:

                index = index + 1

                if number in graph_sel_a:
                    post_index = index
                    grouped.append(number)

                if number not in graph_sel_a or number == graph_sel_a[-1]:
                    if len(grouped) != 0:
                        rule_group = []

                        rule_group.append(keys_tail[post_index - len(grouped)])
                        rule_group.append(grouped)
                        rule_group.append(keys_tail[post_index + 1])

                        chuncks.append(rule_group)
                    grouped = []

            for rule in chuncks:
                group = []
                key_n = 0
                for key in rule[1]:

                    if mod == 0:
                        if key_n == 0:
                            left_n = rule[0]
                        else:
                            left_n = rule[1][key_n - 1]

                        last_key_sel = rule[1][len(rule[1]) - 1]  # is the last key'
                        following_key = rule[0]  # ' is the  key to blend to'

                        firt_val = cmds.keyframe(curve, query=True, valueChange=True, time=(rule[1][0], rule[1][0]))[0]
                        next_val = cmds.keyframe(curve, query=True, valueChange=True, time=(rule[0], rule[0]))[0]
                        gap = next_val - firt_val  # is the difference'

                        dist_to_travel = next_val - firt_val
                        keyrange = rule[1][len(rule[1]) - 1] - rule[1][0]

                        if len(rule[1]) != 1:
                            move_percentage = ((key_n) / float(len(rule[1]) - 1) * -1 + 1)
                        else:
                            move_percentage = 1.0
                        curval = cmds.keyframe(curve, query=True, valueChange=True, time=(key, key))[0]
                        group.append(curval + (dist_to_travel * move_percentage))

                    if mod == 1:  # shift modifier
                        if key_n == 0:
                            left_n = rule[0]
                        else:
                            left_n = rule[1][key_n - 1]
                        if key_n == len(rule[1]) - 1:
                            right_n = rule[2]
                        else:
                            right_n = rule[1][key_n + 1]

                        prev_key_fr = rule[0]
                        next_key_fr = rule[2]
                        prev_key_val = cmds.keyframe(curve, query=True, valueChange=True, time=(left_n, left_n))[0]
                        next_key_val = cmds.keyframe(curve, query=True, valueChange=True, time=(right_n, right_n))[0]
                        group.append(prev_key_val - (prev_key_val - next_key_val) / (right_n - left_n) * (key - left_n))

                    if mod == 9:  # alt + shift modifier
                        # group.append(cmds.keyframe(curve, query=True, valueChange=True, time = (rule[0],rule[0]) )[0])
                        prev_key_fr = rule[0]
                        next_key_fr = rule[2]
                        prev_key_val = cmds.keyframe(curve, query=True, valueChange=True, time=(rule[0], rule[0]))[0]
                        next_key_val = cmds.keyframe(curve, query=True, valueChange=True, time=(rule[2], rule[2]))[0]
                        group.append(
                            prev_key_val - (prev_key_val - next_key_val) / (rule[2] - rule[0]) * (key - rule[0]))

                    if mod == 4 and curve != 'visibility':  # ctrl modifier
                        group.append(0)

                    group.append(key)
                    group.append(cmds.keyframe(curve, query=True, valueChange=True, time=(key, key))[0])

                    if mod == 0:
                        if key_n == 0:
                            left_n = rule[0]
                        else:
                            left_n = rule[1][key_n - 1]

                        last_key_sel = rule[1][len(rule[1]) - 1]  # is the last key'
                        following_key = rule[2]  # ' is the next key to blend to'

                        last_val = cmds.keyframe(curve, query=True, valueChange=True,
                                                 time=(rule[1][len(rule[1]) - 1], rule[1][len(rule[1]) - 1]))[0]
                        next_val = cmds.keyframe(curve, query=True, valueChange=True, time=(rule[2], rule[2]))[0]
                        gap = next_val - last_val  # is the difference'

                        dist_to_travel = next_val - last_val
                        keyrange = rule[1][len(rule[1]) - 1] - rule[1][0]

                        if len(rule[1]) != 1:
                            move_percentage = ((key_n) / float(len(rule[1]) - 1))
                        else:
                            move_percentage = 1.0
                        curval = cmds.keyframe(curve, query=True, valueChange=True, time=(key, key))[0]
                        group.append(curval + (dist_to_travel * move_percentage))

                    if mod == 1:  # shift modifier
                        if key_n == 0:
                            left_n = rule[0]
                        else:
                            left_n = rule[1][key_n - 1]
                        if key_n == len(rule[1]) - 1:
                            right_n = rule[2]
                        else:
                            right_n = rule[1][key_n + 1]

                        prev_key_fr = rule[0]
                        next_key_fr = rule[2]
                        prev_key_val = cmds.keyframe(curve, query=True, valueChange=True, time=(left_n, left_n))[0]
                        cur_val = cmds.keyframe(curve, query=True, valueChange=True, time=(key, key))[0]
                        next_key_val = cmds.keyframe(curve, query=True, valueChange=True, time=(right_n, right_n))[0]
                        median = prev_key_val - (prev_key_val - next_key_val) / (right_n - left_n) * (key - left_n)
                        group.append(cur_val - median + cur_val)

                    if mod == 9:  # alt + shift modifier
                        prev_key_fr = rule[0]
                        next_key_fr = rule[2]
                        prev_key_val = cmds.keyframe(curve, query=True, valueChange=True, time=(rule[0], rule[0]))[0]
                        cur_val = cmds.keyframe(curve, query=True, valueChange=True, time=(key, key))[0]
                        next_key_val = cmds.keyframe(curve, query=True, valueChange=True, time=(rule[2], rule[2]))[0]
                        median = prev_key_val - (prev_key_val - next_key_val) / (rule[2] - rule[0]) * (key - rule[0])
                        group.append(cur_val - median + cur_val)

                    if mod == 4 and curve != 'visibility':  # ctrl modifier
                        next_val = cmds.keyframe(curve, query=True, valueChange=True, time=(key, key))[0] * 2
                        group.append(next_val)

                    group.append(curve)
                    if not group[0] == group[2] == group[3]:
                        graph_keys_rules.append(group)

                    group = []
                    key_n = key_n + 1
        return graph_keys_rules, graph_sel


def pre_opperation():
    """Ran prior to draggins slider"""
    cmds.undoInfo(openChunk=True, chunkName='TWeener')

    graph_sel = cmds.keyframe(query=True, selected=True, name=True)

    ani_attr = get_aniattr()

    auto_key_pref = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)

    return auto_key_pref, ani_attr


def is_timeline_sel():
    """Return True if use has a selection on the timerange"""
    g_play_back_slider = mel.eval('$temp=$gPlayBackSlider')
    range_array = cmds.timeControl(g_play_back_slider, q=1, rangeArray=1)
    timesel = (range_array[1] - range_array[0])
    if timesel == 1.0:
        return False
    else:
        return True


def check_if_sel_empty():
    """Return True if selection is empty"""
    if len(cmds.ls(selection=True)) == 0:
        return True
    else:
        return False


def post_opperation(auto_key_pref, graph_sel):
    """Run as at the very last, after the slider is released"""
    if auto_key_pref is True:
        cmds.autoKeyframe(state=True)

    if graph_sel is None:
        cmds.setKeyframe()

    cmds.undoInfo(stateWithoutFlush=True, undoName='TWeener')
    cmds.undoInfo(closeChunk=True, chunkName='TWeener')
