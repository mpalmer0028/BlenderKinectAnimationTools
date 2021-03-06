"""Kinect Animation Tools addon for Blender"""
from typing import Tuple

from numpy.lib import angle
import bpy
import os, math
import mathutils, numpy as np
from bpy.props import FloatProperty, IntProperty, PointerProperty
from bpy.types import Armature, PropertyGroup, Struct, UIList, Operator, Panel, Menu
from collections import namedtuple

try:
    from scipy import stats
except ImportError:
    import subprocess
    import sys

    # path to python.exe
    python_exe = sys.executable
    lib_folder =  sys.executable.split('bin\\')[0]+'lib'

    # upgrade pip
    subprocess.call([python_exe, "-m", "ensurepip"])
    subprocess.call([python_exe, "-m", "pip", "install", "--upgrade", "pip"])

    # install required packages
    subprocess.call([python_exe, "-m", "pip", "install","--target="+lib_folder,  "scipy"])
    from scipy import stats

bl_info = {
    "name": "Kinect Animation Tools",
    "author": "Mitchell Palmer",
    "version": (0, 0, 1),
    "blender": (2, 93, 0),
    "location": "3D View > Sidebar > Kinect",
    "description": "Add tools for using Kinect data for animation",
    "warning": "",
    "category": "Animation",
}
"""Info for Blender"""

"""Data Classes"""
ExtraBoneStruct = namedtuple("ExtraBoneStruct", "name head_pos parent")

class KeyframeRotation:
    """For storing rotation keyframe data"""
    def __init__(self, time, index, quaternion, w, x, y ,z):
        self.time = time
        self.index = index
        self.quaternion = quaternion
        self.w = w
        self.x = x
        self.y = y
        self.z = z
    
    def __str__(self):
        return "KeyframeRotation: "+ str(self.time)
    def __repr__(self):
        return self.__str__()

class KeyframeBetween:
    """For storing rotation keyframe data"""
    def __init__(self, start_key, end_key):
        self.start_key = start_key
        self.end_key = end_key
        self.pass_filter = True
    
    def __str__(self):
        return "KeyframeBetween: "+ ("P" if self.pass_filter else "F") + ' ' + str((self.start_key.time + self.end_key.time) / 2)
    def __repr__(self):
        return self.__str__()

class NoiseSpike:
    """For storing noise spike data"""
    def __init__(self, before_key, after_key, middle_keys):
        self.before_key = before_key
        self.after_key = after_key
        self.middle_keys = middle_keys
    
    def __str__(self):
        if len(self.middle_keys) > 1:
            return "NoiseSpike: "+ str((self.middle_keys)) +' '+ str(len(self.middle_keys))
        else:
            return "NoiseSpike: "+ str((self.middle_keys))
    def __repr__(self):
        return self.__str__()

"""Operators"""
class AlignMetarigAndKinectRig(Operator):
    """Align metarig(Rigify) and Kinect rig"""  # Use this as a tooltip for menu items and buttons.
    bl_description = "Make metarig(from Rigify) align with a Kinect rig"
    bl_idname = "scene.align_metarig_and_kinect_rig"
    # Unique identifier for buttons and menu items to reference.
    bl_label = "Align metarig(Rigify) with Kinect rig"         # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.

    def execute(self, context):
        if not isinstance(context.scene.kinect_retarget_rig_from, bpy.types.Object):
            raise TypeError("Must have a Kinect rig set")
        if not isinstance(context.scene.kinect_retarget_rig_to, bpy.types.Object):
            raise TypeError("Must have a metarig set")
        # set to first frame 
        bpy.context.scene.frame_set(0)

        kinect_rig = context.scene.kinect_retarget_rig_from
        metarig = context.scene.kinect_retarget_rig_to
        prefix = kinect_rig.name.split(":")[0] + ":"

        # add kinect rig correction objects
        if bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        if kinect_rig.parent is None:
            bpy.ops.object.empty_add(type="SINGLE_ARROW")
            rotation_empty = context.selected_objects[0]
            bpy.ops.object.empty_add(type="PLAIN_AXES")
            location_empty = context.selected_objects[0]
        else:
            rotation_empty = kinect_rig.parent
            location_empty = rotation_empty.parent

        inverse_roll_empty = bpy.context.scene.objects.get("InverseRollEmpty")
        if not inverse_roll_empty:
            bpy.ops.object.empty_add(type="SINGLE_ARROW", rotation=(0, 3.14159, 0), location=(0, 0, 10))
            inverse_roll_empty = context.selected_objects[0]

        rotation_empty.name = "KinectRotationCorrection"
        kinect_rig.parent = rotation_empty
        location_empty.name = "KinectPositionCorrection"
        rotation_empty.parent = location_empty
        inverse_roll_empty.name = "InverseRollEmpty"

        rotation_empty.show_name = True
        location_empty.show_name = True
        inverse_roll_empty.show_name = True

        # add bones
        kinect_rig.select_set(True)
        bpy.context.view_layer.objects.active = kinect_rig
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)

        edit_bones = kinect_rig.data.edit_bones
        try:
            hip_corrected =  edit_bones["hip_corrected"]
        except KeyError:
            hip_corrected = edit_bones.new("hip_corrected")
        hip_corrected.parent = edit_bones[prefix + "Hips"]
        hip_corrected.head = edit_bones[prefix + "Hips"].head
        hip_corrected.tail = edit_bones[prefix + "Hips"].tail
        hip_corrected.roll = 0#3.141593

        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        metarig.select_set(True)
        bpy.context.view_layer.objects.active = metarig
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)

        up_vec = mathutils.Vector((0,0,.15))
        edit_bones = metarig.data.edit_bones
        try:
            elbow_position_l =  edit_bones["elbow_position.L"]
        except KeyError:
            elbow_position_l = edit_bones.new("elbow_position.L")
        elbow_position_l.head = edit_bones["upper_arm.L"].tail
        elbow_position_l.tail = (mathutils.Vector(edit_bones["upper_arm.L"].tail)+up_vec)[:]

        try:
            elbow_position_r =  edit_bones["elbow_position.R"]
        except KeyError:
            elbow_position_r = edit_bones.new("elbow_position.R")
        elbow_position_r.head = edit_bones["upper_arm.R"].tail
        elbow_position_r.tail = (mathutils.Vector(edit_bones["upper_arm.R"].tail)+up_vec)[:]

        try:
            knee_position_l =  edit_bones["knee_position.L"]
        except KeyError:
            knee_position_l = edit_bones.new("knee_position.L")
        knee_position_l.head = edit_bones["shin.L"].head
        knee_position_l.tail = (mathutils.Vector(edit_bones["shin.L"].head)+up_vec)[:]

        try:
            knee_position_r =  edit_bones["knee_position.R"]
        except KeyError:
            knee_position_r = edit_bones.new("knee_position.R")
        knee_position_r.head = edit_bones["shin.R"].head
        knee_position_r.tail = (mathutils.Vector(edit_bones["shin.R"].head)+up_vec)[:]

        try:
            root =  edit_bones["root"]
        except KeyError:
            root = edit_bones.new("root")
        root.head = (0,0,0)
        root.tail = up_vec[:]
        metarig.data.edit_bones["spine"].parent =  metarig.data.edit_bones["root"]

        try:
            foot_target_l =  edit_bones["foot_target.L"]
        except KeyError:
            foot_target_l = edit_bones.new("foot_target.L")
        foot_target_l.head = (0,0,0)
        foot_target_l.tail = up_vec[:]
        foot_target_l.parent = edit_bones["shin.L"]


        try:
            foot_target_r =  edit_bones["foot_target.R"]
        except KeyError:
            foot_target_r = edit_bones.new("foot_target.R")
        foot_target_r.head = (0,0,0)
        foot_target_r.tail = up_vec[:]
        foot_target_r.parent = edit_bones["shin.R"]


        # add metarig constraints
        bpy.ops.object.mode_set(mode='POSE', toggle=False)
        bpy.ops.pose.select_all(action="DESELECT")

        metarig.data.bones["elbow_position.L"].select = True
        metarig.data.bones["elbow_position.R"].select = True
        metarig.data.bones["knee_position.L"].select = True
        metarig.data.bones["knee_position.R"].select = True
        metarig.data.bones["root"].select = True
        metarig.data.bones["foot_target.L"].select = True
        metarig.data.bones["foot_target.R"].select = True

        bpy.ops.pose.constraints_clear()

        subtarget_map = {
            "elbow_position.L": prefix + "LeftForeArm",
            "elbow_position.R": prefix + "RightForeArm",
            "knee_position.L": prefix + "LeftLeg",
            "knee_position.R": prefix + "RightLeg",
            "foot_target.L": "foot.L",
            "foot_target.R": "foot.R",
            "root": prefix + "Hips",
        }

        for pose_bone in context.selected_pose_bones_from_active_object:
            copy_rot = (pose_bone.constraints.get("CopyRot")
                    or pose_bone.constraints.new(type='COPY_ROTATION'))
            copy_rot.name = "CopyRot"
            copy_rot.target = metarig
            copy_rot.subtarget = "root"

            copy_pos = (pose_bone.constraints.get("CopyPos")
                    or pose_bone.constraints.new(type='COPY_LOCATION'))
            copy_pos.name = "CopyPos"
            copy_pos.target = kinect_rig
            copy_pos.subtarget = subtarget_map[pose_bone.name]
            copy_pos.use_z = pose_bone.name != "root"
        bpy.ops.pose.select_all(action="DESELECT")

        metarig.data.bones["foot_target.L"].select = True
        metarig.data.bones["foot_target.R"].select = True

        bpy.ops.pose.constraints_clear()
        for pose_bone in context.selected_pose_bones_from_active_object:
            copy_pos = (pose_bone.constraints.get("CopyPos")
                    or pose_bone.constraints.new(type='COPY_LOCATION'))
            copy_pos.name = "CopyPos"
            copy_pos.target = metarig
            copy_pos.subtarget = subtarget_map[pose_bone.name]
            
            limit_pos = (pose_bone.constraints.get("LimitPos")
                    or pose_bone.constraints.new(type='LIMIT_LOCATION'))
            limit_pos.name = "LimitPos"
            limit_pos.use_min_z = True
            limit_pos.min_z = 1
            limit_pos.owner_space = 'LOCAL'

        bpy.ops.pose.select_all(action="DESELECT")
        # Rotate kinect
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        bpy.ops.object.select_all(action="DESELECT")
        if rotation_empty.rotation_euler[0] == 0:
            v_1 = kinect_rig.data.bones[prefix + "Hips"].head - \
                kinect_rig.data.bones[prefix + "Hips"].tail
            v_2 = (0,-1,0)
            rotation_empty.rotation_euler[0] = v_1.angle(v_2)

        # Scale kinect
        kinect_rig.select_set(True)
        # deselect the other bones
        for bone in kinect_rig.data.bones: 
            bone.select = False
            bone.select_tail = False
            bone.select_head = False
        # select hip head for pos
        kinect_rig.data.bones["hip_corrected"].select_head = True
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)

        old_transform_pivot_point = bpy.context.scene.tool_settings.transform_pivot_point
        old_cursor_location = bpy.context.scene.cursor.location

        # snap cursor to head
        bpy.context.scene.tool_settings.transform_pivot_point = 'MEDIAN_POINT'
        bpy.ops.view3d.snap_cursor_to_selected()

        kinect_rig_hip_location = bpy.context.scene.cursor.location
        kinect_rig_height = kinect_rig_hip_location.z

        # get metarig height
        spine = metarig.data.bones["spine"]
        metarig_height = spine.head.z * metarig.scale.z

        # set new scale for kinect rig
        kinect_rig_scale = metarig_height / kinect_rig_height * kinect_rig.scale.z
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        if kinect_rig_scale != kinect_rig.scale.x:
            # print(kinect_rig_scale,location_empty.scale.x)
            kinect_rig.scale = (kinect_rig_scale, kinect_rig_scale, kinect_rig_scale)

        # position kinect rig on y
        if abs(metarig.data.bones["spine"].head.y - location_empty.location.y) > .05:
            location_empty.location.y = metarig.data.bones["spine"].head.y

        # put cursor back
        bpy.context.scene.cursor.location = old_cursor_location
        bpy.context.scene.tool_settings.transform_pivot_point = old_transform_pivot_point

        bpy.ops.object.select_all(action='DESELECT')
        kinect_rig.select_set(True)

        # add kinect rig constaints
        bpy.ops.object.mode_set(mode='POSE', toggle=False)
        # deselect the other bones
        for bone in kinect_rig.data.bones:
            bone.select = False
            bone.select_tail = False
            bone.select_head = False
        kinect_rig.data.bones[prefix + "Hips"].select = True
        bpy.ops.pose.constraints_clear()
        # print(context.selected_pose_bones)
        for pose_bone in context.selected_pose_bones:
            # print(pose_bone)
            if pose_bone.name == prefix + "Hips":
                copy_corrected_pos = (pose_bone.constraints.get("Lock Pos To Position Correction")
                        or pose_bone.constraints.new(type='COPY_LOCATION'))
                copy_corrected_pos.name = "Lock Pos To Position Correction"
                copy_corrected_pos.target = location_empty
                copy_corrected_pos.use_x = True
                copy_corrected_pos.use_y = True
                copy_corrected_pos.use_z = False
                copy_corrected_pos.target_space = "WORLD"
                copy_corrected_pos.owner_space = "WORLD"

        translation = mathutils.Vector(metarig.data.bones["spine"].head) - mathutils.Vector(kinect_rig_hip_location)
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        metarig.select_set(True)
        kinect_rig.select_set(True)
        bpy.context.view_layer.objects.active = kinect_rig
        # move kinect bones on y axis to line up with metarig
        # deselect the metarig bones
        for bone in metarig.data.bones:
            bone.select = False
            bone.select_tail = False
            bone.select_head = False
        # select the kinect_rig bones
        for bone in kinect_rig.data.bones:
            bone.select = True
            bone.select_tail = True
            bone.select_head = True
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.context.scene.tool_settings.use_snap = True
        bpy.context.scene.tool_settings.snap_elements = {'VERTEX'}
        bpy.context.scene.tool_settings.transform_pivot_point = 'MEDIAN_POINT'
        bpy.ops.transform.translate(value=translation[:], orient_type='GLOBAL', \
            orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL', \
            constraint_axis=(False, True, False), mirror=True, use_proportional_edit=False, \
            proportional_edit_falloff='SMOOTH', proportional_size=1, \
            use_proportional_connected=False, use_proportional_projected=False)
        # deselect the kinect_rig bones
        for bone in kinect_rig.data.bones:
            bone.select = False
            bone.select_tail = False
            bone.select_head = False

        # snap kinect bones to metarig bones
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)

        edit_bones = kinect_rig.data.edit_bones
        # deselect the kinect_rig bones
        for bone in edit_bones:
            bone.select = False
            bone.select_tail = False
            bone.select_head = False

        # Move kinect rig to match meta rig
        # Bones with direct match
        # (kinect bone name, bone to target name)
        bone_strs = [(prefix+"Hips", "spine"),("hip_corrected", "spine"),\
            (prefix+"Head", "spine.005"),\
            (prefix+"Neck", "spine.004"),\
            (prefix+"Spine", "spine.003"),\
            (prefix+"LeftArm", "upper_arm.L"),(prefix+"RightArm", "upper_arm.R"),\
            (prefix+"LeftShoulder", "shoulder.L"),(prefix+"RightShoulder", "shoulder.R"),\
            (prefix+"LeftForeArm", "forearm.L"),(prefix+"RightForeArm", "forearm.R"),\
            (prefix+"LeftUpLeg", "thigh.L"),(prefix+"RightUpLeg", "thigh.R"),\
            (prefix+"LeftLeg", "shin.L"),(prefix+"RightLeg", "shin.R"),\
            (prefix+"LeftFoot", "foot.L"),(prefix+"RightFoot", "foot.R"),\
            (prefix+"LeftToeBase", "toe.L"),(prefix+"RightToeBase", "toe.R")
                ]
        for bone_str in bone_strs:
            # snap cursor to head
            metarig.data.edit_bones[bone_str[1]].select_head = True
            bpy.ops.view3d.snap_cursor_to_selected()
            metarig.data.edit_bones[bone_str[1]].select_head = False
            # snap head to cursor
            kinect_rig.data.edit_bones[bone_str[0]].select_head = True
            bpy.ops.view3d.snap_selected_to_cursor(use_offset=False)
            kinect_rig.data.edit_bones[bone_str[0]].select_head = False

            # snap cursor to tail
            metarig.data.edit_bones[bone_str[1]].select_tail = True
            bpy.ops.view3d.snap_cursor_to_selected()
            metarig.data.edit_bones[bone_str[1]].select_tail = False
            # snap tail to cursor
            kinect_rig.data.edit_bones[bone_str[0]].select_tail = True
            bpy.ops.view3d.snap_selected_to_cursor(use_offset=False)
            kinect_rig.data.edit_bones[bone_str[0]].select_tail = False

        # Bones with indirect match
        # (kinect bone head name, bone head to target name, kinect bone tail name, bone tail to target name)
        bone_strs = [\
            (prefix+"Spine", "spine.002", prefix+"Spine", "spine.003")\
                ]
        for bone_str in bone_strs:
            # snap cursor to head
            metarig.data.edit_bones[bone_str[1]].select_head = True
            bpy.ops.view3d.snap_cursor_to_selected()
            metarig.data.edit_bones[bone_str[1]].select_head = False
            # snap head to cursor
            kinect_rig.data.edit_bones[bone_str[0]].select_head = True
            bpy.ops.view3d.snap_selected_to_cursor(use_offset=False)
            kinect_rig.data.edit_bones[bone_str[0]].select_head = False

            # snap cursor to tail
            metarig.data.edit_bones[bone_str[3]].select_tail = True
            bpy.ops.view3d.snap_cursor_to_selected()
            metarig.data.edit_bones[bone_str[3]].select_tail = False
            # snap tail to cursor
            kinect_rig.data.edit_bones[bone_str[2]].select_tail = True
            bpy.ops.view3d.snap_selected_to_cursor(use_offset=False)
            kinect_rig.data.edit_bones[bone_str[2]].select_tail = False

        # Match arm rotation one metarig
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        kinect_rig.select_set(False)
        # kinect_rig.select_set(True)
        # bpy.ops.object.hide_view_set(unselected=False)
        metarig.select_set(True)
        bpy.context.view_layer.objects.active = metarig
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.context.scene.tool_settings.use_snap = False
        bpy.context.object.data.use_mirror_x = False
        bpy.ops.armature.select_all(action='DESELECT')
        bpy.context.object.data.use_mirror_x = True

        # arm rotation
        for bone_name in ["upper_arm.L","forearm.L"]:
            for axis in [(1,'Y'),(2,'Z')]:
                # Get vectors
                bpy.context.object.data.use_mirror_x = False
                bpy.context.scene.tool_settings.transform_pivot_point = 'MEDIAN_POINT'
                bpy.ops.armature.select_all(action='DESELECT')

                # v_1
                metarig.data.edit_bones[bone_name].select_head = True
                bpy.ops.view3d.snap_cursor_to_selected()
                vector_1 = bpy.context.scene.cursor.location.copy()
                # print(axis[1], bpy.context.scene.cursor.location)
                metarig.data.edit_bones[bone_name].select_head = False

                # v_1
                metarig.data.edit_bones[bone_name].select_tail = True
                bpy.ops.view3d.snap_cursor_to_selected()
                vector_2 = bpy.context.scene.cursor.location.copy()
                # print(axis[1], bpy.context.scene.cursor.location)
                metarig.data.edit_bones[bone_name].select_tail = False

                # snap cursor to head
                metarig.data.edit_bones[bone_name].select_head = True
                bpy.ops.view3d.snap_cursor_to_selected()
                metarig.data.edit_bones[bone_name].select_head = False
                bpy.ops.armature.select_all(action='DESELECT')

                # select whole arm
                metarig.data.edit_bones[bone_name].select = True
                metarig.data.edit_bones.active = metarig.data.edit_bones[bone_name]
                bpy.ops.armature.select_similar(type='CHILDREN')

                vertor_direction = vector_2-vector_1
                vertor_direction[axis[0]] = 0
                turn_angle = mathutils.Vector((1,0,0)).angle(vertor_direction, 0)

                if bone_name == "forearm.L" and axis[1] == 'Z':
                    turn_angle = -turn_angle

                bpy.context.scene.tool_settings.transform_pivot_point = 'CURSOR'
                # print(turn_angle)
                if turn_angle > 0.5:
                    # print(bone_name, axis[1],  math.degrees(turn_angle), vertor_direction)
                    bpy.context.object.data.use_mirror_x = True
                    bpy.ops.transform.rotate(value=turn_angle, orient_axis=axis[1], \
                        center_override=vector_1[:], orient_type='GLOBAL')
                bpy.ops.armature.select_all(action='DESELECT')

        # set elbow position location
        edit_bones = metarig.data.edit_bones
        try:
            elbow_position_l =  edit_bones["elbow_position.L"]
        except KeyError:
            elbow_position_l = edit_bones.new("elbow_position.L")
        elbow_position_l.head = edit_bones["upper_arm.L"].tail
        elbow_position_l.tail = (mathutils.Vector(edit_bones["upper_arm.L"].tail)+up_vec)[:]

        try:
            elbow_position_r =  edit_bones["elbow_position.R"]
        except KeyError:
            elbow_position_r = edit_bones.new("elbow_position.R")
        elbow_position_r.head = edit_bones["upper_arm.R"].tail
        elbow_position_r.tail = (mathutils.Vector(edit_bones["upper_arm.R"].tail)+up_vec)[:]

        # place kinect arms
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        kinect_rig.select_set(True)
        metarig.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.context.object.data.use_mirror_x = False
        bpy.ops.armature.select_all(action='DESELECT')
        bpy.context.scene.tool_settings.use_snap = True
        bpy.context.scene.tool_settings.snap_elements = {'VERTEX'}
        bpy.context.scene.tool_settings.transform_pivot_point = 'MEDIAN_POINT'
        bpy.context.object.data.use_mirror_x = True

        for bone_str in [\
            (prefix+'LeftArm', 'upper_arm.L'),(prefix+'RightArm', 'upper_arm.R'),\
            (prefix+'LeftForeArm', 'forearm.L'),(prefix+'RightForeArm', 'forearm.R'),\
            (prefix+'LeftHand', 'hand.L'),(prefix+'RightHand', 'hand.R')\
                ]:

            # snap cursor to head
            metarig.data.edit_bones[bone_str[1]].select_head = True
            bpy.ops.view3d.snap_cursor_to_selected()
            metarig.data.edit_bones[bone_str[1]].select_head = False
            # snap head to cursor
            kinect_rig.data.edit_bones[bone_str[0]].select_head = True
            bpy.ops.view3d.snap_selected_to_cursor(use_offset=False)
            kinect_rig.data.edit_bones[bone_str[0]].select_head = False

            # snap cursor to tail
            metarig.data.edit_bones[bone_str[1]].select_tail = True
            bpy.ops.view3d.snap_cursor_to_selected()
            metarig.data.edit_bones[bone_str[1]].select_tail = False
            # snap tail to cursor
            kinect_rig.data.edit_bones[bone_str[0]].select_tail = True
            bpy.ops.view3d.snap_selected_to_cursor(use_offset=False)
            kinect_rig.data.edit_bones[bone_str[0]].select_tail = False

        return {'FINISHED'}

class RetargetMetarigToKinectRig(Operator):
    """Retarget metarig(Rigify) to Kinect rig"""  # Use this as a tooltip for menu items and buttons.
    bl_description = "Make metarig(from Rigify) target a rig from a Kinect recording"
    bl_idname = "scene.retarget_metarig_to_kinect_rig"
    # Unique identifier for buttons and menu items to reference.
    bl_label = "Retarget metarig(Rigify) to Kinect rig"         # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.

    extra_bones_for_metarig = []
    extra_bones_for_kinect = []

    def execute(self, context):
        if not isinstance(context.scene.kinect_retarget_rig_from, bpy.types.Object):
            raise TypeError("Must have a Kinect rig set")
        if not isinstance(context.scene.kinect_retarget_rig_to, bpy.types.Object):
            raise TypeError("Must have a metarig set")
        # set to first frame 
        bpy.context.scene.frame_set(0)

        kinect_rig = context.scene.kinect_retarget_rig_from
        metarig = context.scene.kinect_retarget_rig_to
        prefix = kinect_rig.name.split(":")[0] + ":"

        # add kinect rig correction objects
        if bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        inverse_roll_empty = bpy.context.scene.objects.get("InverseRollEmpty")
        if not inverse_roll_empty:
            bpy.ops.object.empty_add(type="SINGLE_ARROW", rotation=(0, 3.14159, 0), location=(0, 0, 10))
            inverse_roll_empty = context.selected_objects[0]

        inverse_roll_empty.name = "InverseRollEmpty"
        inverse_roll_empty.show_name = True

        # Select rig
        bpy.ops.object.select_all(action='DESELECT')

        # Add bone constaints to metarig
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        metarig.select_set(True)
        kinect_rig.select_set(False)
        bpy.context.view_layer.objects.active = metarig

        bpy.ops.object.mode_set(mode='POSE', toggle=False)
        # deselect the other bones
        for bone in metarig.data.bones:
            bone.select = False
            bone.select_tail = False
            bone.select_head = False

        metarig.data.bones["root"].select = True
        # Spine
        metarig.data.bones["spine"].select = True
        metarig.data.bones["spine.002"].select = True
        metarig.data.bones["spine.004"].select = True
        metarig.data.bones["spine.005"].select = True
        metarig.data.bones["face"].select = True
        # Arms
        metarig.data.bones["upper_arm.L"].select = True
        metarig.data.bones["upper_arm.R"].select = True
        metarig.data.bones["forearm.L"].select = True
        metarig.data.bones["forearm.R"].select = True
        metarig.data.bones["hand.L"].select = True
        metarig.data.bones["hand.R"].select = True
        # Legs
        metarig.data.bones["thigh.L"].select = True
        metarig.data.bones["thigh.R"].select = True
        metarig.data.bones["shin.L"].select = True
        metarig.data.bones["shin.R"].select = True
        metarig.data.bones["foot.L"].select = True
        metarig.data.bones["foot.R"].select = True
        metarig.data.bones["toe.L"].select = True
        metarig.data.bones["toe.R"].select = True

        metarig.data.bones.active = metarig.data.bones["root"]
        bpy.ops.pose.constraints_clear()

        copied_bones_rot = [("spine","hip_corrected"),("spine.002",prefix+"Spine"),\
            ("spine.004",prefix+"Neck"),\
            ("forearm.L",prefix+"LeftForeArm"),("forearm.R",prefix+"RightForeArm"),\
            ("upper_arm.L",prefix+"LeftArm"),("upper_arm.R",prefix+"RightArm"),\
            ("hand.L",prefix+"LeftHand"),("hand.R",prefix+"RightHand"),\
            ("thigh.L",prefix+"LeftUpLeg"),("thigh.R",prefix+"RightUpLeg"),\
            ("shin.L",prefix+"LeftLeg"),("shin.R",prefix+"RightLeg"),\

            # ("foot.L",prefix+"LeftFoot"),("foot.R",prefix+"RightFoot")\
            # ("toe.L",prefix+"LeftToeBase"),("toe.R",prefix+"RightToeBase")\
                ]
        inverse_rolled_bones_rot = [
            "shin.L","shin.R",
            # "foot.L","foot.R"
        ]
        ik_tracks = [("foot.L", "foot_target.L"),("foot.R", "foot_target.R"),]
        # (pose_bone.name, subtarget, head_tail(0 is head)
        copied_bones_damped_track = []
        for pose_bone in context.selected_pose_bones:
            copy_rot = [item for item in copied_bones_rot if item[0] == pose_bone.name]
            ik_track = [item for item in ik_tracks if item[0] == pose_bone.name]
            copy_damped_track = [item for item in copied_bones_damped_track \
                if item[0] == pose_bone.name]
            if pose_bone.name == "root":
                copy_spine_loc = (pose_bone.constraints.get("Spine Location Copy")
                                or pose_bone.constraints.new(type='COPY_LOCATION')) 
                copy_spine_loc.name = "Spine Location Copy"
                copy_spine_loc.target = kinect_rig
                copy_spine_loc.subtarget = "hip_corrected"
                copy_spine_loc.use_x = True
                copy_spine_loc.use_y = True
                copy_spine_loc.use_z = False

                copy_spine_rot = (pose_bone.constraints.get("Spine Rotation Copy")
                                or pose_bone.constraints.new(type='COPY_ROTATION'))
                copy_spine_rot.name = "Spine Rotation Copy"
                copy_spine_rot.target = kinect_rig
                copy_spine_rot.subtarget = "hip_corrected"
                copy_spine_rot.use_x = False
                copy_spine_rot.use_y = False
                copy_spine_rot.use_z = True
            elif pose_bone.name == "spine":
                copy_spine_loc = (pose_bone.constraints.get("Spine Location Copy")
                                or pose_bone.constraints.new(type='COPY_LOCATION'))
                copy_spine_loc.name = "Spine Location Copy"
                copy_spine_loc.target = kinect_rig
                copy_spine_loc.subtarget = "hip_corrected"

                copy_spine_rot = (pose_bone.constraints.get("Spine Rotation Copy")
                                or pose_bone.constraints.new(type='COPY_ROTATION'))
                copy_spine_rot.name = "Spine Rotation Copy"
                copy_spine_rot.target = kinect_rig
                copy_spine_rot.subtarget = "hip_corrected"
            elif pose_bone.name == "spine.002":
                copy_spine_loc = (pose_bone.constraints.get("Spine Location Copy")
                                or pose_bone.constraints.new(type='COPY_LOCATION'))
                copy_spine_loc.name = "Spine Location Copy"
                copy_spine_loc.target = kinect_rig
                copy_spine_loc.subtarget = prefix+"Spine"

                copy_spine_rot = (pose_bone.constraints.get("Spine Rotation Copy")
                                or pose_bone.constraints.new(type='COPY_ROTATION'))
                copy_spine_rot.name = "Spine Rotation Copy"
                copy_spine_rot.target = kinect_rig
                copy_spine_rot.subtarget = prefix+"Spine"
            elif pose_bone.name == "spine.004":
                copy_spine_loc = (pose_bone.constraints.get("Spine Location Copy")
                                or pose_bone.constraints.new(type='COPY_LOCATION'))
                copy_spine_loc.name = "Spine Location Copy"
                copy_spine_loc.target = kinect_rig
                copy_spine_loc.subtarget = prefix+"Neck"

                copy_spine_rot = (pose_bone.constraints.get("Spine Rotation Copy")
                                or pose_bone.constraints.new(type='COPY_ROTATION'))
                copy_spine_rot.name = "Spine Rotation Copy"
                copy_spine_rot.target = kinect_rig
                copy_spine_rot.subtarget = prefix+"Neck"
                # copy_spine_rot.target_space = "LOCAL"
                # copy_spine_rot.owner_space = "LOCAL"
            elif pose_bone.name == "spine.005":
                copy_spine_loc = (pose_bone.constraints.get("Spine Location Copy")
                                or pose_bone.constraints.new(type='COPY_LOCATION'))
                copy_spine_loc.name = "Spine Location Copy"
                copy_spine_loc.target = kinect_rig
                copy_spine_loc.subtarget = prefix+"Head"
                # copy_spine_loc.target_space = "LOCAL"
                # copy_spine_loc.owner_space = "LOCAL"

                copy_spine_rot = (pose_bone.constraints.get("Spine Rotation Copy")
                                or pose_bone.constraints.new(type='COPY_ROTATION'))
                copy_spine_rot.name = "Spine Rotation Copy"
                copy_spine_rot.target = kinect_rig
                copy_spine_rot.subtarget = prefix+"Head"
                # copy_spine_rot.target_space = "LOCAL"
                # copy_spine_rot.owner_space = "LOCAL"
            elif pose_bone.name == "face":
                # copy_spine_rot = (pose_bone.constraints.get("Head Rotation Copy")
                #                 or pose_bone.constraints.new(type='COPY_ROTATION'))
                # copy_spine_rot.name = "Spine Rotation Copy"
                # copy_spine_rot.target = kinect_rig
                # copy_spine_rot.subtarget = prefix+"Head"
                
                copy_inverse_rot_con = (pose_bone.constraints.get("Inverse Bone Roll Rotation Add")
                                or pose_bone.constraints.new(type='COPY_ROTATION'))
                copy_inverse_rot_con.name = "Inverse Bone Roll Rotation Add"
                copy_inverse_rot_con.target = inverse_roll_empty
                copy_inverse_rot_con.mix_mode = "ADD"
                copy_inverse_rot_con.euler_order = 'YZX'

            elif copy_rot:
                copy_rot_con = (pose_bone.constraints.get(copy_rot[0][0]+" Rotation Copy")
                                or pose_bone.constraints.new(type='COPY_ROTATION'))
                copy_rot_con.name = copy_rot[0][0]+" Rotation Copy"
                copy_rot_con.target = kinect_rig
                copy_rot_con.subtarget = copy_rot[0][1]
                # copy_rot_con.target_space = "LOCAL"
                # copy_rot_con.owner_space = "LOCAL"
                copy_rot_con.target_space = "WORLD"
                copy_rot_con.owner_space = "WORLD"
                if copy_rot[0][0] in inverse_rolled_bones_rot:
                    copy_inverse_rot_con = (pose_bone.constraints.get("Inverse Bone Roll Rotation Add")
                                or pose_bone.constraints.new(type='COPY_ROTATION'))
                    copy_inverse_rot_con.name = "Inverse Bone Roll Rotation Add"
                    copy_inverse_rot_con.target = inverse_roll_empty
                    copy_inverse_rot_con.mix_mode = "ADD"
                    if copy_rot[0][0].startswith("shin"):
                        copy_inverse_rot_con.euler_order = 'YZX'
                        copy_inverse_rot_con.influence = .5
                        if copy_rot[0][0] == "shin.L":
                            copy_inverse_rot_con.invert_y = True
                    # elif copy_rot[0][0].startswith("foot"):
                    #     copy_inverse_rot_con.euler_order = 'YZX'

            # elif copy_damped_track:
            #     damped_track = (pose_bone.constraints.get("Follow Bone")
            #                     or pose_bone.constraints.new(type='DAMPED_TRACK'))
            #     damped_track.name = "Follow Bone"
            #     damped_track.target = metarig
            #     damped_track.subtarget = copy_damped_track[0][1]
            #     damped_track.head_tail = copy_damped_track[0][2]

            elif ik_track:
                ik_track_con = (pose_bone.constraints.get("Follow Target")
                                or pose_bone.constraints.new(type='IK'))
                ik_track_con.name = "Follow Target"
                ik_track_con.target = metarig
                ik_track_con.subtarget = ik_track[0][1]
                ik_track_con.chain_count = 1
                ik_track_con.iterations = 25


            # if copy_spine_loc:
            #     copy_spine_loc.target_space = "LOCAL"
            #     copy_spine_loc.owner_space = "LOCAL"
            # if copy_spine_rot:
            #     copy_spine_rot.target_space = "LOCAL"
            #     copy_spine_rot.owner_space = "LOCAL"
            # if copy_rot_con:
            #     copy_rot_con.target_space = "LOCAL"
            #     copy_rot_con.owner_space = "LOCAL"
            

        return {'FINISHED'}

class CleanKinectAnimationData(Operator):
    """Clean Kinect animation data"""  # Use this as a tooltip for menu items and buttons.
    bl_description = "Clean animation noise/errors from kinect motion capture data"
    bl_idname = "animation.clean_kinect_animation"
    # Unique identifier for buttons and menu items to reference.
    bl_label = "Clean Kinect animation data" # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.

    def execute(self, context):
        if not isinstance(context.scene.kinect_retarget_rig_from, bpy.types.Object):
            raise TypeError("Must have a Kinect rig set")

        # set to first frame 
        bpy.context.scene.frame_set(0)

        kinect_rig = context.scene.kinect_retarget_rig_from

        # select kinect rig
        if bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        bpy.ops.object.select_all(action='DESELECT')
        kinect_rig.select_set(True)
        bpy.context.view_layer.objects.active = kinect_rig

        bpy.ops.object.mode_set(mode='POSE', toggle=False)

        # print(kinect_rig.animation_data.action)
        # print(kinect_rig.animation_data.action.fcurves)
        max_noise_spike_width = context.scene.max_noise_spike_width
        max_noise_spike_angle = context.scene.max_noise_spike_angle

        # build rotation data for each frame
        rotation_data = {}
        context.window_manager.progress_begin(0, len(kinect_rig.data.bones)*2)
        progress_i = 0
        for bone in kinect_rig.data.bones:
            # get quaternion curves
            w = kinect_rig.animation_data.action.fcurves.find("pose.bones[\""+bone.name+"\"].rotation_quaternion", index=0)
            x = kinect_rig.animation_data.action.fcurves.find("pose.bones[\""+bone.name+"\"].rotation_quaternion", index=1)
            y = kinect_rig.animation_data.action.fcurves.find("pose.bones[\""+bone.name+"\"].rotation_quaternion", index=2)
            z = kinect_rig.animation_data.action.fcurves.find("pose.bones[\""+bone.name+"\"].rotation_quaternion", index=3)

            if w and x and y and z:
                # define empty lists if quaternion data exists
                rotation_data[bone.name]={'keyframes': [],'rotations_between_frames': [], 'spikes':[]}                
                for index, key_w in enumerate(w.keyframe_points):
                    q = mathutils.Quaternion((key_w.co[1], x.keyframe_points[index].co[1], y.keyframe_points[index].co[1], z.keyframe_points[index].co[1]))
                    rotation_data[bone.name]['keyframes'].append(KeyframeRotation(key_w.co[0], index, q, key_w, x.keyframe_points[index], y.keyframe_points[index], z.keyframe_points[index]))
                    # print(key_w.co[0], q)
            # for index, curve in enumerate(kinect_rig.animation_data.action.fcurves):
            #     if curve.data_path.endswith('rotation_quaternion'):
                    
            #     #     for key in curve.keyframe_points:
            #     #         # The curve's points has a 'co' vector giving the frame and the value
            #     #         print( 'frame: ', key.co[0], ' value: ', key.co[1] )
            progress_i += 1
            context.window_manager.progress_update(progress_i)
        # print(rotation_data)

        # build inbetween frames
        for bone_name in rotation_data:
            # go over each frame
            for index, keyframe in enumerate(rotation_data[bone_name]['keyframes']):
                if index < len(rotation_data[bone_name]['keyframes'])-1:
                    data_between = KeyframeBetween(keyframe, rotation_data[bone_name]['keyframes'][index+1])
                    q_between = data_between.start_key.quaternion.rotation_difference(data_between.end_key.quaternion)
                    t_between = data_between.end_key.time - data_between.start_key.time
                    data_between.pass_filter = (q_between.angle / t_between) < max_noise_spike_angle
                    # print(index, np.arctan(q_between.angle / t_between))
                    rotation_data[bone_name]['rotations_between_frames'].append(data_between)
            # print(bone_name,len(rotation_data[bone_name]['keyframes']),len(rotation_data[bone_name]['rotations_between_frames']))
            # print(sorted(rotation_data[bone_name]['rotations_between_frames'], reverse=True))
            # if 'LeftLeg' in bone_name:
                
            # test_a =np.array(rotation_data[bone_name]['rotations_between_frames'])
            # result = stats.zscore(test_a,ddof=1)
            inbetweens = rotation_data[bone_name]['rotations_between_frames']

            inbetweens_length = len(inbetweens)
            # go over each inbetween 
            for i, inbetween in  enumerate(inbetweens):
                # real_i = inbetweens_length - i
                # does this frame pass and is it after the second frame
                if not inbetween.pass_filter and i > 1:
                    # check for spikes in different sizes
                    for i_away in reversed(range(1,max_noise_spike_width+1)):
                        # Look for two failing inbetweens sandwiching passing inbetweens
                        # end fail already checked
                        # if "LeftLeg" in bone_name: 
                        #     print('index',i, 'away', i_away, 'frame',)# rotation_data[bone_name]['keyframes'][i].time)
                        has_spike = True
                        for sandwich_i in range(i+1,i+i_away):
                            # print(sandwich_i,"pass" if inbetweens[sandwich_i].pass_filter else "fail")
                            if sandwich_i >= inbetweens_length:
                                has_spike = False
                                break
                            elif not inbetweens[sandwich_i].pass_filter:
                                has_spike = False
                                break
                        # check last inbetween
                        end_cap_i = i+i_away+1 
                        if has_spike and end_cap_i < inbetweens_length and not inbetweens[end_cap_i].pass_filter: 
                            # if "LeftLeg" in bone_name:
                            #     print("spike found", rotation_data[bone_name]['keyframes'][i+1:end_cap_i])
                            rotation_data[bone_name]['spikes'].append(NoiseSpike(inbetween.end_key,inbetweens[end_cap_i].start_key,\
                                rotation_data[bone_name]['keyframes'][i+1:end_cap_i]))
                            break
        # progress_i += 1
        # context.window_manager.progress_update(progress_i)
        for bone_name in rotation_data:
            if len(rotation_data[bone_name]['spikes']) > 0: # and "LeftLeg" in bone_name:
                # print('summary', bone_name)
                for spikes in reversed(rotation_data[bone_name]['spikes']):
                    for keyframe in reversed(spikes.middle_keys):
                        # print(keyframe)
                        w = kinect_rig.animation_data.action.fcurves.find("pose.bones[\""+bone_name+"\"].rotation_quaternion", index=0).keyframe_points
                        x = kinect_rig.animation_data.action.fcurves.find("pose.bones[\""+bone_name+"\"].rotation_quaternion", index=1).keyframe_points
                        y = kinect_rig.animation_data.action.fcurves.find("pose.bones[\""+bone_name+"\"].rotation_quaternion", index=2).keyframe_points
                        z = kinect_rig.animation_data.action.fcurves.find("pose.bones[\""+bone_name+"\"].rotation_quaternion", index=3).keyframe_points
                        
                        w.remove(w[keyframe.index])
                        x.remove(x[keyframe.index])
                        y.remove(y[keyframe.index])
                        z.remove(z[keyframe.index])
        # context.window_manager.progress_end();
                    

        return {'FINISHED'}

"""Panels"""
class VIEW3D_PT_kinect_animation_tools_retarget_to_rigify(Panel):
    """Retarget To Rigify"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Kinect"
    bl_label = "Retarget To Rigify"

    def draw(self, context):
        layout = self.layout
        scene = bpy.data.scenes[0]
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        col = layout.column(align=True, heading="Retarget Metarig")
        col.prop(scene,"kinect_retarget_rig_from")
        col.prop(scene,"kinect_retarget_rig_to")
        col.operator("scene.align_metarig_and_kinect_rig", text="Align")
        col.operator("scene.retarget_metarig_to_kinect_rig", text="Retarget")

class VIEW3D_PT_kinect_clean_animation_data(Panel):
    """Clean Kinect data"""
    bl_space_type = 'GRAPH_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Kinect"
    bl_label = "Clean Kinect data"

    def draw(self, context):
        layout = self.layout
        scene = bpy.data.scenes[0]
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        col = layout.column(align=True, heading="Clean Kinect data")
        col.prop(scene,"kinect_retarget_rig_from")

        col.prop(scene,"max_noise_spike_angle")
        col.prop(scene,"max_noise_spike_width")
        col.operator("animation.clean_kinect_animation", text="Clean Kinect Rotations")

"""Registering"""
classes = [RetargetMetarigToKinectRig, AlignMetarigAndKinectRig, CleanKinectAnimationData,
    VIEW3D_PT_kinect_animation_tools_retarget_to_rigify, VIEW3D_PT_kinect_clean_animation_data
]

def register():
    os.system("cls")
    """Register properties"""
    bpy.types.Scene.kinect_retarget_rig_from = PointerProperty(
        name="Kinect Rig", type=bpy.types.Object, 
        description="Rig gotten from you kinect recording")

    bpy.types.Scene.kinect_retarget_rig_to = PointerProperty(
        name="Rigify metarig", type=bpy.types.Object,
        description="Rig(your Rigify metarig) that will be targeting the kinect rig")

    bpy.types.Scene.max_noise_spike_width = IntProperty(
        name="Max Spike Width",
        default=6,
        # step=2,
        min=1,
        description="Maximum width in keyframes of animation error/noise spikes to filter out.")

    bpy.types.Scene.max_noise_spike_angle = FloatProperty(
        name="Max Spike Angle",
        default=.3 ,
        step=10,
        min=.00001,
        description="Maximum angle in between keyframes of animation error/noise spikes to filter out.")

    """Register classes"""
    for cls in classes:
        bpy.utils.register_class(cls)
        print(cls.__name__ +" registered")

    
def unregister():
    """Unregister classes"""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    """Unregister properties"""
    del bpy.types.Scene.kinect_retarget_rig_from
    del bpy.types.Scene.kinect_retarget_rig_to
    del bpy.types.Scene.max_noise_spike_width
    del bpy.types.Scene.max_noise_spike_angle

if __name__ == "__main__":
    register()
