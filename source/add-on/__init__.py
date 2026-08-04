bl_info = {
    "name"        : "Mallet",
    "author"      : "luxreduxdelux",
    "version"     : (1, 0, 0),
    "blender"     : (5, 2, 0),
    "location"    : "View3D > Sidebar",
    "description" : "Game engine agnostic entity editor for Blender.",
    "category"    : "3D View",
}

#================================================================

from . import general
from . import blender

#================================================================

def register():
    blender.register()

def unregister():
    blender.unregister()