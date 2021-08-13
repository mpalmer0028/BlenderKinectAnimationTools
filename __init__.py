"""Kinect Animation Tools addon for Blender"""
import bpy
from bpy.props import EnumProperty, PointerProperty
from bpy.types import PropertyGroup, UIList, Operator, Panel, Menu
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

"""Operators"""
class RetargetMetarigToKinectRig(Operator):
    """Retarget metarig(Rigify) to Kinect rig"""  # Use this as a tooltip for menu items and buttons.
    bl_description = "Make metarig(from Rigify) target a rig from a Kinect recording"
    bl_idname = "scene.retarget_metarig_to_kinect_rig"
    # Unique identifier for buttons and menu items to reference.
    bl_label = "Retarget metarig(Rigify) to Kinect rig"         # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.

    def execute(self, context):

        return {'FINISHED'}
        
"""Panels"""
class VIEW3D_PT_kinect_animation_tools_retarget_to_rigify(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Kinect"
    bl_label = "Retarget To Rigify"

    def draw(self, context):
        layout = self.layout
        scene = bpy.data.scenes[0]
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        col = layout.column(align=True, heading="Show")
        col.prop(scene,"kinect_retarget_rig_from")
        col.prop(scene,"kinect_retarget_rig_to")
        col.operator("scene.retarget_metarig_to_kinect_rig")
# Registering
classes = [RetargetMetarigToKinectRig, VIEW3D_PT_kinect_animation_tools_retarget_to_rigify]

def register():
    """Register properties"""
    bpy.types.Scene.kinect_retarget_rig_from = bpy.props.PointerProperty(
        name="Kinect Rig", type=bpy.types.Object, 
        description="Rig gotten from you kinect recording")

    bpy.types.Scene.kinect_retarget_rig_to = bpy.props.PointerProperty(
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
