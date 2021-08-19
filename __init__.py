"""Kinect Animation Tools addon for Blender"""
import bpy
import os
import mathutils
from bpy.props import EnumProperty, PointerProperty
from bpy.types import Armature, PropertyGroup, UIList, Operator, Panel, Menu
from collections import namedtuple
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

ExtraBoneStruct = namedtuple("ExtraBoneStruct", "name head_pos parent")

"""Operators"""
class RetargetMetarigToKinectRig(Operator):
    """Retarget metarig(Rigify) to Kinect rig"""  # Use this as a tooltip for menu items and buttons.
    bl_description = "Make metarig(from Rigify) target a rig from a Kinect recording"
    bl_idname = "scene.retarget_metarig_to_kinect_rig"
    # Unique identifier for buttons and menu items to reference.
    bl_label = "Retarget metarig(Rigify) to Kinect rig"         # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.

    extra_bones_for_metarig = []
    extra_bones_for_kinect = []

    # def add_kinect_constraints(self, kinect_rig, metarig, context):
    #     # select kinect rig
    #     bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    #     kinect_rig.select_set(True)
    #     bpy.context.view_layer.objects.active = kinect_rig
    #     bpy.ops.object.mode_set(mode='POSE', toggle=False)
    #     bpy.ops.pose.select_all(action="DESELECT")
    #     print(self.left_foot.name)
    #     print(self.right_foot.name)
    #     left_foot = kinect_rig.data.bones[self.left_foot.name]
    #     right_foot = kinect_rig.data.bones[self.right_foot.name]

    #     left_foot.select = True
    #     right_foot.select = True

    #     bpy.ops.pose.constraints_clear()

    #     for pose_bone in context.selected_pose_bones_from_active_object:
    #         # use if already existes, else create
    #         if pose_bone.name in [self.left_foot.name,self.right_foot.name]:
    #             limit_rot = (pose_bone.constraints.get("LimitRot")
    #                     or pose_bone.constraints.new(type='LIMIT_ROTATION'))
    #             limit_rot.name = "LimitRot"
    #             limit_rot.use_limit_x = True
    #             limit_rot.use_limit_y = True

    #             limit_pos = (pose_bone.constraints.get("LimitPos")
    #                     or pose_bone.constraints.new(type='LIMIT_LOCATION'))
    #             limit_pos.name = "LimitPos"
    #             limit_pos.use_min_z = True
    #         if pose_bone.name in [self.left_hand.name, self.right_hand.name]:
    #             pass
    #             # track_to_name = "TrackTo"
    #             # track_to = (pose_bone.constraints.get(track_to_name)
    #             #         or pose_bone.constraints.new(type='TRACK_TO'))
    #             # track_to.name = track_to_name
    #             # track_to.track_axis =  'TRACK_NEGATIVE_Y'
    #             # track_to.up_axis =  'UP_Z'



    def execute(self, context):
        if not isinstance(context.scene.kinect_retarget_rig_from, bpy.types.Object):
            raise TypeError("Must have a Kinect rig set")
        if not isinstance(context.scene.kinect_retarget_rig_to, bpy.types.Object):
            raise TypeError("Must have a target rig set")
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

        rotation_empty.name = "KinectRotationCorrection"
        kinect_rig.parent = rotation_empty
        location_empty.name = "KinectPositionCorrection"
        rotation_empty.parent = location_empty

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
        hip_corrected.roll = 3.141593

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

        # add constraints
        bpy.ops.object.mode_set(mode='POSE', toggle=False)
        bpy.ops.pose.select_all(action="DESELECT")

        metarig.data.bones["elbow_position.L"].select = True
        metarig.data.bones["elbow_position.R"].select = True
        metarig.data.bones["knee_position.L"].select = True
        metarig.data.bones["knee_position.R"].select = True
        metarig.data.bones["root"].select = True

        bpy.ops.pose.constraints_clear()

        subtarget_map = {
            "elbow_position.L": prefix + "LeftForeArm",
            "elbow_position.R": prefix + "RightForeArm",
            "knee_position.L": prefix + "LeftLeg",
            "knee_position.R": prefix + "RightLeg",
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

        # Rotate kinect
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        bpy.ops.object.select_all(action="DESELECT")
        v_1 = kinect_rig.data.bones[prefix + "Hips"].head - kinect_rig.data.bones[prefix + "Hips"].tail
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

        kinect_rig_height = bpy.context.scene.cursor.location.z

        # get metarig height
        spine = metarig.data.bones["spine"]
        metarig_height = spine.head.z * metarig.scale.z

        # set new scale for kinect rig
        kinect_rig_scale = metarig_height / kinect_rig_height * kinect_rig.scale.z
        kinect_rig.scale = (kinect_rig_scale, kinect_rig_scale, kinect_rig_scale)

        # position kinect rig on y
        bpy.ops.view3d.snap_cursor_to_selected()
        kinect_rig_y = bpy.context.scene.cursor.location.y

        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        location_empty.location.y = spine.head.y - kinect_rig_y

        # put cursor back
        bpy.context.scene.cursor.location = old_cursor_location
        bpy.context.scene.tool_settings.transform_pivot_point = old_transform_pivot_point

        # limit_rot = (elbow_position_l.constraints.get("LimitRot")
        #         or elbow_position_l.constraints.new(type='LIMIT_ROTATION'))
        # limit_rot.name = "LimitRot"
        # limit_rot.use_limit_x = True
        # limit_rot.use_limit_y = True

        # limit_pos = (pose_bone.constraints.get("LimitPos")
        #         or pose_bone.constraints.new(type='LIMIT_LOCATION'))
        # limit_pos.name = "LimitPos"
        # limit_pos.use_min_z = True



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
        col.operator("scene.retarget_metarig_to_kinect_rig", text="Retarget")

"""Registering"""
classes = [RetargetMetarigToKinectRig, VIEW3D_PT_kinect_animation_tools_retarget_to_rigify]

def register():
    os.system("cls")
    """Register properties"""
    bpy.types.Scene.kinect_retarget_rig_from = PointerProperty(
        name="Kinect Rig", type=bpy.types.Object, 
        description="Rig gotten from you kinect recording")

    bpy.types.Scene.kinect_retarget_rig_to = PointerProperty(
        name="Target Rig", type=bpy.types.Object,
        description="Rig(your Rigify metarig) that will be targeting the kinect rig")

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

if __name__ == "__main__":
    register()
