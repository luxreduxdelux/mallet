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

META         = None
GAME_PROCESS = None

def load_meta(scene, path):
    global META

    with open(path) as file:
        META = general.Meta(json.load(file))

    scene.entity_list.clear()
    scene.meta_path = path

    #================

    object_data = {}

    for field_name, field in META.object.items():
        object_data[field_name] = field.get_blender_property()

    ObjectData = type("ObjectData", (bpy.types.PropertyGroup,), { "__annotations__": object_data })

    bpy.utils.register_class(ObjectData)

    setattr(bpy.types.Object, "object_data", bpy.props.PointerProperty(type=ObjectData))

    #================

    for entity_name in META.entity:
        entity_data = {}
        entity      = META.entity[entity_name]

        item        = scene.entity_list.add()
        item.name   = entity.name
        item.index  = entity_name

        for field_name in entity.field:
            field                   = entity.field[field_name]
            entity_data[field_name] = field.get_blender_property()

        EntityData = type(entity_name, (bpy.types.PropertyGroup,), { "__annotations__": entity_data })

        bpy.utils.register_class(EntityData)

        setattr(bpy.types.Object, entity_name, bpy.props.PointerProperty(type=EntityData))

def draw_field(box, field_name, field, entity_data):
    if field.kind == general.FieldKind.INDEX or field_name in entity_data:
        box.prop(entity_data, field_name)
    else:
        row = box.row()
        row.prop(entity_data, field_name)
        row.label(icon="WARNING_LARGE")

def get_view_camera(context):
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            region_3d = area.spaces.active.region_3d
            location = region_3d.view_matrix.inverted().translation
            rotation = region_3d.view_rotation.to_euler()

            return (location, rotation)

def get_entity_browser_entity(context):
    index = context.scene.entity_list_index

    if META != None and index >= 0 and index < len(context.scene.entity_list):
        entity_index = context.scene.entity_list[index].index

        if entity_index in META.entity:
            return (META.entity[entity_index], entity_index)

#================================================================
# Panel section.
#================================================================

class PanelMain(bpy.types.Panel):
    bl_label       = "Mallet"
    bl_idname      = "mallet.panel_main"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "Mallet"

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text = "General", icon = "TOOL_SETTINGS")

        row = box.row()

        if context.scene.meta_path != "" and META != None:
            row.operator("mallet.import_meta",      icon = "FILE_REFRESH")
            row.operator("mallet.import_meta_file", icon = "IMPORT", text = "")

            row = box.row()

            if context.scene.game_path != "":
                row.operator("mallet.game_launch",      icon = "PLAY")
                row.operator("mallet.import_game_path", icon = "IMPORT", text = "")
                box.prop(context.scene, "game_launch_point")
                box.prop(context.scene, "game_launch_angle")
            else:
                row.operator("mallet.import_game_path", icon = "IMPORT")

            #================

            box = layout.box()
            box.label(text = "Import/Export", icon = "FILE")

            row = box.row()
            row.operator("mallet.import_glb", icon = "IMPORT")

            if context.scene.save_path_glb != "":
                row.operator("mallet.export_glb_fast", icon = "EXPORT")
                row.operator("mallet.export_glb",      icon = "EXPORT", text = "")
            else:
                row.operator("mallet.export_glb", icon = "EXPORT")

            row = box.row()
            row.operator("mallet.import_json", icon = "IMPORT")

            if context.scene.save_path_json != "":
                row.operator("mallet.export_json_fast", icon = "EXPORT")
                row.operator("mallet.export_json",      icon = "EXPORT", text = "")
            else:
                row.operator("mallet.export_json", icon = "EXPORT")

            if "torch" in bpy.context.preferences.addons:
                box.prop(context.scene, "torch_bake")

            #================

            entity_browser = get_entity_browser_entity(context)

            box = layout.box()
            box.label(text = "Entity Browser", icon = "CUBE")

            if entity_browser != None:
                entity_browser = entity_browser[0]
                box.label(text = " " + entity_browser.info)

            box.template_list(
                "PanelMainEntityList",
                "",
                context.scene,
                "entity_list",
                context.scene,
                "entity_list_index"
            )
            box.operator("mallet.entity_insert")

            #================

            active = bpy.context.object

            if active != None:
                if "entity_index" in active:
                    entity_index = active["entity_index"]
                    entity       = META.entity[entity_index]

                    if entity.field:
                        box = layout.box()
                        box.label(text = "Entity Editor", icon = "EMPTY_DATA")

                        active_entity_data = getattr(active, entity_index)

                        for field_name, field in entity.field.items():
                            draw_field(box, field_name, field, active_entity_data)

                    if entity.body.kind == general.BodyKind.OBJECT:
                        if META.object:
                            box = layout.box()
                            box.label(text = "Object Editor", icon = "OBJECT_DATA")

                            for field_name, field in META.object.items():
                                draw_field(box, field_name, field, active.object_data)

                elif META.object:
                    box = layout.box()
                    box.label(text = "Object Editor", icon = "OBJECT_DATA")

                    for field_name, field in META.object.items():
                        draw_field(box, field_name, field, active.object_data)
        else:
            row.operator("mallet.import_meta_file", icon = "IMPORT")

class PanelMainEntityList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.prop(item, "name", text="", emboss=False)

class PanelMainEntityListItem(bpy.types.PropertyGroup):
    name  : bpy.props.StringProperty()
    index : bpy.props.StringProperty()

#================================================================
# Operator section.
#================================================================

class OperatorMeta(Operator):
    """Re-import the active meta file."""
    bl_idname    = "mallet.import_meta"
    bl_label     = "Re-Load Meta"

    def execute(self, context):
        load_meta(context.scene, context.scene.meta_path)

        return {'FINISHED'}

def export_scene_glb(scene, path):
    if "torch" in bpy.context.preferences.addons and scene.torch_bake:
        bpy.ops.torch.bake()

    bpy.ops.export_scene.gltf(
        filepath      = path,
        export_format = "GLB",
        export_extras = True,
    )

class OperatorGameLaunch(bpy.types.Operator):
    """Launch a game."""
    bl_idname = "mallet.game_launch"
    bl_label  = "Launch Game"

    def execute(self, context):
        global GAME_PROCESS

        folder = Path(context.scene.game_path).parent
        level  = str(folder / "level.glb")

        Path(folder / "level.glb").unlink(missing_ok=True)
        export_scene_glb(context.scene, level)

        (point, angle) = get_view_camera(context)
        point = META.editor.blender_to_user_vector(point)

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
        if context.scene.torch_bake:
            environment["MALLET_TORCH_BAKE"] = "1"

        if GAME_PROCESS != None:
            GAME_PROCESS.kill()

        GAME_PROCESS = subprocess.Popen([context.scene.game_path], cwd=folder, env=environment)

        return {'FINISHED'}

class OperatorEntityInsert(bpy.types.Operator):
    """Insert an entity using the active entity browser index."""
    bl_idname = "mallet.entity_insert"
    bl_label  = "Insert Entity"

    def execute(self, context):
        entity_browser = get_entity_browser_entity(context)

        if entity_browser != None:
            entity, entity_index = entity_browser
            object = None

            if entity.body.kind == general.BodyKind.OBJECT:
                # TO-DO do check if active object is a mesh or not
                object = bpy.context.object
            else:
                object = bpy.data.objects.new(entity.name, None)
                object.empty_display_type = entity.body.get_blender_body()
                object.scale              = META.editor.user_to_blender_vector(entity.body.size)

            if object != None:
                object.show_name       = True
                object.show_axis       = True
                object["entity_index"] = entity_index

                if META.editor.always_initialize:
                    for field_name, field in entity.field.items():
                        if field.kind != general.FieldKind.INDEX:
                            setattr(getattr(object, entity_index), field_name, field.data)

                if object.name not in bpy.context.collection.objects:
                    bpy.context.collection.objects.link(object)
                    object.select_set(True)
                    bpy.context.view_layer.objects.active = object
                    # TO-DO de-select all, invoke this, make sure new entity isn't a model
                    # bpy.ops.transform.translate(
                    #     'INVOKE_DEFAULT',
                    #     orient_type='LOCAL',
                    #     constraint_axis=(True, True, False),
                    # )

        return {'FINISHED'}

#================================================================
# Import/Export section.
#================================================================

class ImportGLB(Operator, ImportHelper):
    bl_idname    = "mallet.import_glb"
    bl_label     = "Import .GLB"
    filename_ext = ".glb"

    filter_glob: StringProperty(
        default = "*.glb",
        options = {'HIDDEN'},
        maxlen  = 255,
    )

    def execute(self, context):
        bpy.ops.import_scene.gltf(
            filepath = self.filepath
        )

        return {'FINISHED'}

class ExportGLB(Operator, ExportHelper):
    bl_idname    = "mallet.export_glb"
    bl_label     = "Export .GLB"
    filename_ext = ".glb"

    filter_glob: StringProperty(
        default = "*.glb",
        options = {'HIDDEN'},
        maxlen  = 255,
    )

    def execute(self, context):
        context.scene.save_path_glb = self.filepath
        export_scene_glb(context.scene, self.filepath)

        return {'FINISHED'}

class ExportGLBFast(Operator):
    bl_idname    = "mallet.export_glb_fast"
    bl_label     = "Export .GLB"

    def execute(self, context):
        if context.scene.save_path_glb != "":
            export_scene_glb(context.scene, context.scene.save_path_glb)

        return {'FINISHED'}

class ImportJSON(Operator, ImportHelper):
    bl_idname    = "mallet.import_json"
    bl_label     = "Import .JSON"
    filename_ext = ".json"

    filter_glob: StringProperty(
        default = "*.json",
        options = {'HIDDEN'},
        maxlen  = 255,
    )

    def execute(self, context):
        return {'FINISHED'}

class ExportJSON(Operator, ExportHelper):
    bl_idname    = "mallet.export_json"
    bl_label     = "Export .JSON"
    filename_ext = ".json"

    filter_glob: StringProperty(
        default = "*.json",
        options = {'HIDDEN'},
        maxlen  = 255,
    )

    def execute(self, context):
        return {'FINISHED'}

class ExportJSONFast(Operator):
    bl_idname    = "mallet.export_json_fast"
    bl_label     = "Export .JSON"

    def execute(self, context):
        return {'FINISHED'}

class ImportMetaFile(Operator, ImportHelper):
    """Import a meta file."""
    bl_idname    = "mallet.import_meta_file"
    bl_label     = "Import Meta"
    filename_ext = ".json"

    filter_glob: StringProperty(
        default = "*.json",
        options = {'HIDDEN'},
        maxlen  = 255,
    )

    def execute(self, context):
        load_meta(context.scene, self.filepath)

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
    OperatorEntityInsert,
    ImportGLB,
    ExportGLB,
    ExportGLBFast,
    ImportJSON,
    ExportJSON,
    ExportJSONFast,
    ImportMetaFile,
    ImportGamePath,
]

from bpy.app.handlers import persistent

@persistent
def on_load(_a, _b):
    if bpy.context.scene.meta_path:
        print("[Mallet] Re-loading meta file: " + bpy.context.scene.meta_path)
        load_meta(bpy.context.scene, bpy.context.scene.meta_path)

def register():
    for c in CLASS_LIST:
        bpy.utils.register_class(c)

    bpy.app.handlers.load_post.append(on_load)
    bpy.types.Scene.entity_list       = bpy.props.CollectionProperty(type=PanelMainEntityListItem)
    bpy.types.Scene.entity_list_index = bpy.props.IntProperty(default=-1)
    bpy.types.Scene.meta_path = bpy.props.StringProperty(
        name    = "Meta Path",
        subtype = "FILE_PATH",
    )
    bpy.types.Scene.save_path_glb = bpy.props.StringProperty(
        name    = "Save Path (.GLB)",
        subtype = "FILE_PATH",
    )
    bpy.types.Scene.save_path_json = bpy.props.StringProperty(
        name    = "Save Path (.JSON)",
        subtype = "FILE_PATH",
    )
    bpy.types.Scene.game_path = bpy.props.StringProperty(
        name    = "Game Path",
        subtype = "FILE_PATH",
    )
    bpy.types.Scene.game_launch_point = bpy.props.BoolProperty(
        name        = "Launch With View-Port Point",
        description = "Pass the view-port camera point as an environment variable to the game."
    )
    bpy.types.Scene.game_launch_angle = bpy.props.BoolProperty(
        name        = "Launch With View-Port Angle",
        description = "Pass the view-port camera angle as an environment variable to the game."
    )
    bpy.types.Scene.torch_bake = bpy.props.BoolProperty(
        name        = "Bake With Torch Before Export",
        description = "Use Torch to bake the light-map before exporting. This will also apply to the Launch Game operator."
    )

def unregister():
    global META

    del bpy.types.Scene.entity_list
    del bpy.types.Scene.entity_list_index
    del bpy.types.Scene.meta_path
    del bpy.types.Scene.save_path_glb
    del bpy.types.Scene.save_path_json
    del bpy.types.Scene.game_path
    del bpy.types.Scene.game_launch_point
    del bpy.types.Scene.game_launch_angle
    bpy.app.handlers.load_post.remove(on_load)
    META = None

    for c in CLASS_LIST:
        bpy.utils.unregister_class(c)