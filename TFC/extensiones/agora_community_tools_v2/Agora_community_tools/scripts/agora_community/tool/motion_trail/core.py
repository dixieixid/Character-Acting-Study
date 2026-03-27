import time

from maya.api.OpenMaya import MMatrix, MPoint
import maya.cmds as cmds
import maya.mel as mel

from agora_community import mayalib
from .constants import *


TRAIL_NAME = 'trail'
TRAILSHAPE_NAME = 'agora_trail'


class MotionTrailAgora(object):

    def __init__(self):
        self.check_idle_job = 0
        self.range = []
        self.trail = 'None'
        self.trailshape = 'None'
        self.range_to_process = [1, 2, 3, 4]
        self.ready = True
        self.tracked_object = []
        self.reference_matrix = 'world'
        self.trail_length = 0
        self.first_tracked_frame = 0
        self.trail_points = []
        self.delete_trail()

    def define_object(self):
        selection = cmds.ls(selection=True)
        if not selection:
            LOGGER.warning('Please select at least 1 object.')
            return []

        if (len(selection) == 1 and
                cmds.objectType(selection[0]) == 'mesh'):
            self.mesh_tracker()
        else:
            self.tracked_object = selection
            self.create_dummy_point()

        return self.tracked_object

    def mesh_tracker(self):
        cmds.undoInfo(stateWithoutFlush=False)
        try:
            to_delete = list(filter(cmds.objExists, ['dummyMover', 'trail_keyvisual']))
            if to_delete:
                cmds.delete(to_delete)
            cmds.select(cmds.ls(selection=True, flatten=True)[0])
            mel.eval('Rivet')
            tracker = cmds.rename('pinOutput', 'agora_trail_mesh_tracker')
            cmds.select(tracker)
            cmds.setAttr('{}.visibility'.format(tracker), False)
            cmds.setAttr('{}.hiddenInOutliner'.format(tracker), True)
            self.tracked_object = ['agora_trail_mesh_tracker']
        finally:
            cmds.undoInfo(stateWithoutFlush=True, undoName='TWeener')
        return self.tracked_object

    def delete_trail(self):
        if cmds.objExists(self.trail):
            cmds.delete(self.trail)
        for trail in cmds.ls('{}|{}*'.format(mayalib.get_tool_group(TOOL_NAME), TRAIL_NAME)):
            cmds.delete(TRAIL_NAME)

    def create_trail_node(self):
        '''We're using Maya's standard trail node'''
        self.trail = cmds.createNode('transform', n=TRAIL_NAME, parent=mayalib.get_tool_group(TOOL_NAME), skipSelect=True)
        self.trailshape = cmds.createNode('motionTrailShape', parent=self.trail, n=TRAILSHAPE_NAME, skipSelect=True)
        cmds.commandEcho(filter=['python("from agora_community.tool import motion_trail;', 'from agora_community.tool import motion_trail;'])
        self.set_curve_prettiness('agora_trail')
        cmds.setAttr('{}.hiddenInOutliner'.format(self.trail), True)

        # parenting changes current selection....
        current_selection = (cmds.ls(selection=True))
        if cmds.objExists('agora_trail_mesh_tracker'):
            cmds.setAttr('agora_trail_mesh_tracker.hiddenInOutliner'.format(self.trail), True)
            cmds.parent('agora_trail_mesh_tracker', self.trail)
        cmds.select(current_selection)

    def set_curve_prettiness(self, trail):
        '''Make the curve cute'''
        cmds.setAttr('{}.trailColor'.format(self.trailshape), 1.0, 0.0, 0.0, type='double3')
        cmds.setAttr('{}.extraTrailColor'.format(self.trailshape), 1.0, 1.0, 1.0, type='double3')
        cmds.setAttr('{}.trailDrawMode'.format(self.trailshape), 1)
        cmds.setAttr('{}.template'.format(self.trailshape), True)
        self.set_faded_frames('12')
        cmds.setAttr('agora_trail.increment', 1)

    def set_faded_frames(self, number):
        if number == 'all':
            setting = 0
        else:
            setting = int(number)
        cmds.setAttr('{}.postFrame'.format(self.trailshape), setting)
        cmds.setAttr('{}.preFrame'.format(self.trailshape), setting)
        cmds.setAttr('{}.fadeInoutFrames'.format(self.trailshape), setting)

    def isIdle(self):
        '''First function called when we're idle, will now see if we still have frames to process and process it'''
        if len(self.range_to_process) > 0:
            frame = self.range_to_process.pop(0)
            self.set_frame_point(frame)

    def get_range(self):
        '''Give back to app the range to process stored in this class'''
        return self.range_to_process

    def prioritize_timeline(self):
        '''Set a range to process. If we're on frame 10, will return a list like [10, 11, 9, 12, 8, ...]'''
        in_time = int(cmds.playbackOptions(query=True, minTime=True))
        out_time = int(cmds.playbackOptions(query=True, maxTime=True))
        cur_time = cmds.currentTime(q=True)
        list_of_keys = range(in_time, out_time + 1)
        self.range_to_process = sorted(list_of_keys, key=lambda x: abs(cur_time - x))
        self.trail_length = len(self.range_to_process)
        self.first_tracked_frame = min(self.range_to_process)
        return self.range_to_process

    def create_dummy_point(self):
        '''This is to create the little dot that will be on top of the trail'''
        if not self.tracked_object:
            return

        to_delete = list(filter(cmds.objExists, ['dummyMover', 'trail_keyvisual']))
        if to_delete:
            cmds.delete(to_delete)

        self.keyvisual_group = cmds.createNode('transform', name='dummyMover', parent=TRAIL_NAME, skipSelect=True)
        cmds.setAttr('{}.displayHandle'.format(self.keyvisual_group), True)
        cmds.setAttr('{}.overrideEnabled'.format(self.keyvisual_group), True)
        cmds.setAttr('{}.overrideDisplayType'.format(self.keyvisual_group), 2)
        self.dummytrail = cmds.createNode('transform', name='trail_keyvisual', parent='dummyMover', skipSelect=True)
        self.dummytrailshape = cmds.createNode('motionTrailShape', parent=self.dummytrail, name='trail_keyvisualshape', skipSelect=True)
        cmds.setAttr('{}.keyframeFlags'.format(self.dummytrailshape),2, type='Int32Array')
        cmds.setAttr('{}.points'.format(self.dummytrailshape), 2,(0.0, 0.0, 0.0, 1.0),(0.0, 0.0, 0.0, 1.0),  type='pointArray')
        cmds.setAttr('{}.increment'.format(self.dummytrailshape), 1.0)
        cmds.setAttr('{}.startTime'.format(self.dummytrailshape), 1.0)
        cmds.setAttr('{}.keyframeColor'.format(self.dummytrailshape), 0, 0, 0, type='double3')
        cmds.setAttr('{}.overrideEnabled'.format(self.dummytrailshape), True)
        cmds.setAttr('{}.overrideDisplayType'.format(self.dummytrailshape), 2)
        cmds.connectAttr('{}.message'.format(self.keyvisual_group), '{}.transformToMove'.format(self.dummytrailshape))
        cmds.setAttr('{}.keyframeTimes'.format(self.dummytrailshape), 1, type='doubleArray')
        self.constraint_dummy_point()

    def constraint_dummy_point(self):
        '''This is to constraint the little dot to the tracked object'''
        target_object = self.tracked_object[0]
        constrained_object = self.keyvisual_group

        # Create the constraint
        matrix_constraint = cmds.createNode('multMatrix', skipSelect=True)
        cmds.connectAttr(target_object+'.worldMatrix[0]', matrix_constraint+'.matrixIn[0]')
        cmds.connectAttr(matrix_constraint+'.matrixSum', constrained_object+'.offsetParentMatrix')

    def prepare_pointarray(self, range_time):
        '''Preparing trail's point array to match the whole size of timeline'''
        if self.reference_matrix != 'world':
            self.attach_trail_to_cam()
        original = cmds.getAttr('{}.points'.format(self.trailshape)) or []
        curmatrix = cmds.getAttr(('{}.worldMatrix'.format(self.tracked_object[0])), time=cmds.currentTime(q=True))[
                    12:15]
        if len(original) < len(range_time):
            original = [curmatrix] * len(range_time)
        self.trail_points = original
        cmds.setAttr('{}.startTime'.format(self.trailshape), min(range_time))
        self.set_trail_per_camera_visibility()

    def set_frame_point(self, frame):
        '''processing 1 frame of the "points" channel of the trail'''
        matrixx = cmds.getAttr(('{}.worldMatrix'.format(self.tracked_object[0])), time=frame)[12:16]

        trail_length = self.trail_length
        if self.reference_matrix != 'world' and validate_camera_existance(self.reference_matrix):
            cam_matrixx = cmds.getAttr(('{}.worldMatrix'.format(self.reference_matrix)), time=frame)
            matrix_point = list(MPoint(matrixx) * MMatrix(cam_matrixx).inverse())[:3]
            # trail now has to be under Cam
        else:
            self.reference_matrix = 'world'
            matrix_point = matrixx[:3]
        self.trail_points[frame - int(self.first_tracked_frame)] = matrix_point
        # processing trail should not be added to undo queue
        cmds.undoInfo(stateWithoutFlush=False)
        try:
            cmds.setAttr(
                '{}.points'.format(self.trailshape),
                trail_length,
                * self.trail_points[:trail_length],
                type='pointArray'
            )
        finally:
            cmds.undoInfo(stateWithoutFlush=True, undoName='TWeener')

    def set_camera_reference(self, camera):
        '''Called when changing camera space, we're handling the worldspace connection here'''
        self.reference_matrix = camera
        offset_matrix_attribute = '{}.offsetParentMatrix'.format(self.trail)
        connected_attribute = cmds.listConnections(offset_matrix_attribute, plugs=True)
        if connected_attribute is not None:
            cmds.disconnectAttr(connected_attribute[0], offset_matrix_attribute)
        cmds.setAttr(offset_matrix_attribute,
                     [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0],
                     type="matrix")

    def attach_trail_to_cam(self):
        '''Having the camera controlling the trail node entirely'''
        cam_name = self.reference_matrix
        offset_matrix_attribute = '{}.offsetParentMatrix'.format(self.trail)
        if cmds.objExists(cam_name):
            connected_attribute = cmds.listConnections(offset_matrix_attribute, plugs=True)
            if connected_attribute is None:
                cmds.connectAttr('{}.worldMatrix[0]'.format(cam_name), offset_matrix_attribute)

    def set_trail_per_camera_visibility(self):
        cam_name = self.reference_matrix
        for camera in query_cameras():
            if camera != 'world':
                cmds.perCameraVisibility(self.trail, camera=camera, hide=True, remove=True)
        else:
            if cam_name != 'world':
                mel_command = 'perCameraVisibility -c {} -q -hi'.format(cam_name)
                mel.eval(mel_command)
                for other_camera in query_cameras():
                    if other_camera != cam_name:
                        cmds.perCameraVisibility(self.trail, camera=other_camera, hide=True)


def generic_error(warning_text):
    cmds.warning(warning_text)


def validate_camera_existance(camera):
    '''only check if the camera exists in the scene'''
    if cmds.objExists(camera) or camera == 'world':
        return True

    cmds.warning("The desired camera doesn't exist.")
    return False


def world_matrix(obj):
    """'
    convenience method to get the world matrix of <obj> as a matrix object
    """
    return MMatrix(cmds.xform(obj, q=True, matrix=True, ws=True))


def world_pos(obj):
    """'
    convenience method to get the world position of <obj> as an MPoint
    """
    return MPoint(cmds.xform(obj, q=True, t=True, ws=True))


def query_cameras():
    return cmds.listCameras(p=True)


def kill_jobs():
    '''called to find and close any trail tool script jobs'''
    try:
        cmds.condition('run_trail_job', delete=True)
    except Exception:
        pass  # condition doesn't exists

    for job in cmds.scriptJob(listJobs=True):
        if 'MotionTrailWindow' in job:
            cmds.scriptJob(kill=int(job.split(':')[0]), force=True)


def kill_auto_selection_job():
    '''Using a separate scriptjob to detect automatically selection changes. Killing it now'''
    for job in cmds.scriptJob(listJobs=True):
        if 'define_object' in job:
            cmds.scriptJob(kill=int(job.split(':')[0]), force=True)


def run_script_job_every_n():
    '''Every milisecond (depending on constant value), Return true if Maya is Idle'''
    return round(time.time() * 1000) % 2 == 0


def warning(message):
    cmds.warning(message)
