from . import general

#================================================================

import json
import bpy
import subprocess
import os
from pathlib import Path
from bpy_extras.io_utils import ExportHelper, ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

#================================================================

USER_FILE    = None
GAME_PROCESS = None

def load_user_file(scene, path):
    global USER_FILE

    with open(path) as file:
        USER_FILE = general.UserFile(json.load(file))

    scene.entity_list.clear()
    scene.meta_path = path
    scene.game_path = USER_FILE.editor.path

    for entity in USER_FILE.entity:
        item      = scene.entity_list.add()
        item.name = entity.name.internal

        entity_data = {}

        for field in entity.field:
            entity_data[field.name.external] = field.get_blender_property()

        EntityData = type(entity.name.external, (bpy.types.PropertyGroup,), { "__annotations__": entity_data })

        bpy.utils.register_class(EntityData)

        setattr(bpy.types.Object, entity.name.external, bpy.props.PointerProperty(type=EntityData))

def get_view_camera(context):
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            region_3d = area.spaces.active.region_3d
            location = region_3d.view_matrix.inverted().translation
            rotation = region_3d.view_rotation.to_euler()

            # TO-DO translate from Blender vector to User vector
            return (location, rotation)

#================================================================
# Panel section.
#================================================================

class PanelMain(bpy.types.Panel):
    bl_label       = "Mallet"
    bl_idname      = "PanelMain"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Mallet"

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text = "General", icon = "TOOL_SETTINGS")

        if context.scene.meta_path != "":
            box.operator("mallet.import_meta", icon = "FILE")

        box.operator("mallet.import_meta_file", icon = "IMPORT")
        box.operator("mallet.import_game_path", icon = "IMPORT")

        if USER_FILE != None:
            if context.scene.game_path != "":
                box.operator("mallet.game_launch", icon = "PLAY")
                box.prop(context.scene, "game_launch_point")
                box.prop(context.scene, "game_launch_angle")

            box = layout.box()
            box.label(text = "Entity Picker", icon = "EMPTY_AXIS")
            box.template_list(
                "PanelMainEntityList",
                "",
                context.scene,
                "entity_list",
                context.scene,
                "entity_list_index"
            )
            box.operator("mallet.entity_spawn")

            active = bpy.context.object

            if active != None and "entity_index" in active:
                entity_index = active["entity_index"]
                entity       = USER_FILE.entity[entity_index]

                if entity.field:
                    box = layout.box()
                    box.label(text = "Entity Editor", icon = "OBJECT_DATA")

                    for field in entity.field:
                        box.prop(getattr(active, entity.name.external), field.name.external)

class PanelMainEntityList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.prop(item, "name", text="", emboss=False)

class PanelMainEntityListItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()

#================================================================
# Operator section.
#================================================================

class OperatorMeta(Operator):
    """Re-import the active meta file."""
    bl_idname    = "mallet.import_meta"
    bl_label     = "Re-Load Meta File"

    def execute(self, context):
        load_user_file(context.scene, context.scene.meta_path)

        return {'FINISHED'}

class OperatorGameLaunch(bpy.types.Operator):
    """Launch a game."""
    bl_idname = "mallet.game_launch"
    bl_label  = "Launch Game"

    def execute(self, context):
        global GAME_PROCESS

        folder = Path(context.scene.game_path).parent
        level  = str(folder / "level.glb")

        bpy.ops.export_scene.gltf(
            filepath = level,
            export_format = "GLB",
            export_extras = True,
        )

        (point, angle) = get_view_camera(context)
        point = USER_FILE.editor.blender_to_user_vector(point)

        environment                   = os.environ.copy()
        environment["MALLET_LEVEL"]   = level

        if context.scene.game_launch_point:
            environment["MALLET_POINT_X"] = str(point[0])
            environment["MALLET_POINT_Y"] = str(point[1])
            environment["MALLET_POINT_Z"] = str(point[2])
        if context.scene.game_launch_angle:
            environment["MALLET_ANGLE_X"] = str(angle[0])
            environment["MALLET_ANGLE_Y"] = str(angle[1])
            environment["MALLET_ANGLE_Z"] = str(angle[2])

        if GAME_PROCESS != None:
            GAME_PROCESS.kill()

        GAME_PROCESS = subprocess.Popen([context.scene.game_path], cwd=folder, env=environment)

        return {'FINISHED'}

class OperatorEntitySpawn(bpy.types.Operator):
    """Spawn an entity using the active entity picker index."""
    bl_idname = "mallet.entity_spawn"
    bl_label  = "Spawn Entity"

    def execute(self, context):
        if USER_FILE != None:
            entity_index = context.scene.entity_list_index
            entity       = USER_FILE.entity[entity_index]

            object = None

            if entity.body.kind == general.BodyKind.MODEL:
                # TO-DO do check if active object is a mesh or not
                object = bpy.context.object
            else:
                object = bpy.data.objects.new(entity.name.internal, None)
                object.empty_display_type = entity.body.get_blender_body()
                object.scale              = USER_FILE.editor.user_to_blender_vector(entity.body.size)

            if object != None:
                object.show_name       = True
                object.show_axis       = True
                object["entity_index"] = entity_index

                for field in entity.field:
                    setattr(getattr(object, entity.name.external), field.name.external, field.data)

                if object.name not in bpy.context.collection.objects:
                    bpy.context.collection.objects.link(object)
                    object.select_set(True)
                    bpy.context.view_layer.objects.active = object

        return {'FINISHED'}

#================================================================
# Import/Export section.
#================================================================

class ImportMetaFile(Operator, ImportHelper):
    """Import a meta file."""
    bl_idname    = "mallet.import_meta_file"
    bl_label     = "Import Meta File"
    filename_ext = ".json"

    filter_glob: StringProperty(
        default ="*.json",
        options ={'HIDDEN'},
        maxlen  =255,
    )

    def execute(self, context):
        load_user_file(context.scene, self.filepath)

        return {'FINISHED'}

class ImportGamePath(Operator, ImportHelper):
    """Import a game to launch."""
    bl_idname    = "mallet.import_game_path"
    bl_label     = "Select Game"

    def execute(self, context):
        context.scene.game_path = self.filepath

        return {'FINISHED'}

#================================================================

CLASS_LIST = [
    PanelMain,
    PanelMainEntityList,
    PanelMainEntityListItem,
    OperatorMeta,
    OperatorGameLaunch,
    OperatorEntitySpawn,
    ImportMetaFile,
    ImportGamePath,
]

def register():
    for c in CLASS_LIST:
        bpy.utils.register_class(c)

    bpy.types.Scene.entity_list       = bpy.props.CollectionProperty(type=PanelMainEntityListItem)
    bpy.types.Scene.entity_list_index = bpy.props.IntProperty(default=-1)
    bpy.types.Scene.meta_path = bpy.props.StringProperty(
        name    = "Meta Path",
        subtype = "FILE_PATH",
    )
    bpy.types.Scene.game_path = bpy.props.StringProperty(
        name    = "Game Path",
        subtype = "FILE_PATH",
    )
    bpy.types.Scene.game_launch_point = bpy.props.BoolProperty(
        name    = "Launch With Viewport Point",
    )
    bpy.types.Scene.game_launch_angle = bpy.props.BoolProperty(
        name    = "Launch With Viewport Angle",
    )

def unregister():
    del bpy.types.Scene.entity_list
    del bpy.types.Scene.entity_list_index
    del bpy.types.Scene.meta_path
    del bpy.types.Scene.game_path
    del bpy.types.Scene.game_launch_point
    del bpy.types.Scene.game_launch_angle

    for c in CLASS_LIST:
        bpy.utils.unregister_class(c)