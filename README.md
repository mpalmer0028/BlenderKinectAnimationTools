# BlenderKinectAnimationTools
 This is a Blender addon I wrote to help me automate the process of transferring kinect data that I import to a rigify metarig.
 
 To get your kinect data recorded and imported into Blender as an .fbx check out this tutorial playlist [this tutorial playlist](https://youtube.com/playlist?list=PLZpDYt0cyiuvd2X6ucSYilKJD6rKK2Uys "Blender + Kinect Rigging & Animation - FAST! Royal Skies"). I would recommend watching the whole playlist so you understand what this addon does.
 
 
 ## Getting Started
 1. Install addon in Blender using the __init__.py. Restarting Blender will probably be required if you don't have the Python package scipy
 2. Watch part 1-4 of [this great tutorial](https://youtube.com/playlist?list=PLZpDYt0cyiuvd2X6ucSYilKJD6rKK2Uys "Blender + Kinect Rigging & Animation - FAST! Royal Skies")  by [Royal Skies](https://www.youtube.com/c/RoyalSkiesLLC "Royal Skies youtube channel")
 3. Once you have your Kinect data imported and the addon is installed you should see a Kinect tab in you 3D viewport. Set the Kinect Rig to the rig imported from your .fbx and Rigify metarig to the metarig you would like to use.
 ![Panel preview](./PanelPreview.png "Preview of the Kinect panel in in the 3D viewport")
 4. Hit the Align button to position the rigs for targeting
 5. Hit the Retarget button to add all constraints and adjustments
 6. The metarig should now target the kinect rig.
 7. Since the Kinect data can be far from perfect I've added a Kinect panel to the Graph Editor with a Clean Kinect Rotations button.
 8. Clean Kinect Rotations button attempts to remove large sudden rotation spikes that happen when the Kinect miss calculates a rotation. The existing settings have helped my animations the most, but it is just averaging out the spikes so it has its limitations.
 ![Graph Editor Panel preview](./PanelCleaningPreview.png "Preview of the Kinect panel in in the Graph Editor")
 ### Recommendations
 The [tutorial](https://youtube.com/playlist?list=PLZpDYt0cyiuvd2X6ucSYilKJD6rKK2Uys "Blender + Kinect Rigging & Animation - FAST! Royal Skies")  by [Royal Skies](https://www.youtube.com/c/RoyalSkiesLLC "Royal Skies youtube channel") that this addon is base on includes information on an rig that already has everything setup on a different rig. If you don't want to use a rigify metarig then you can use that or add the constraints manually using the tutorial.
 
 I've also included a demo file [demo .blend file](./ExampleRigFromConvertedKinectFBX.blend) that includes a metarig and imported Kinect rig with animation data.