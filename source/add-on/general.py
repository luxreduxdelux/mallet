import bpy
from dataclasses import dataclass
from enum        import Enum
from mathutils   import Vector

#================================================================

def value_or_default(dictionary: dict, key: str, default: any):
    if key in dictionary:
        return dictionary[key]
    else:
        return default

def value_error(key: str, value: any, value_possible: [any]):
    suggest = ""

    for v in value_possible:
        if suggest == "":
            suggest  = f"{v}"
        else:
            suggest += f", {v}"

    raise ValueError(f"Invalid \"{key}\" value: \"{value}\" (must be one of \"{suggest}\")")

class BodyKind(Enum):
    AXIS   = 0
    CUBOID = 1
    SPHERE = 2
    OBJECT = 3

@dataclass(init=False)
class Body:
    kind: BodyKind
    data: Vector

    def __init__(self, value: dict):
        value = Reader(value, "Body")

        match value_or_default(value, "kind", "cuboid"):
            case "axis":
                self.kind = BodyKind.AXIS
            case "cuboid":
                size = value_or_default(value, "size", [1, 1, 1])
                self.kind = BodyKind.CUBOID
                self.size = Vector((
                    size[0],
                    size[1],
                    size[2],
                ))
            case "sphere":
                size = value_or_default(value, "size", [1, 1, 1])
                self.kind = BodyKind.SPHERE
                self.size = Vector((
                    size[0],
                    size[1],
                    size[2],
                ))
            case "object":
                self.kind = BodyKind.OBJECT
            case x:
                value_error("body", x, ["axis", "cuboid", "sphere", "object"])

    def get_blender_body(self) -> str:
        match self.kind:
            case BodyKind.AXIS:
                return "PLAIN_AXIS"
            case BodyKind.CUBOID:
                return "CUBE"
            case BodyKind.SPHERE:
                return "SPHERE"
            case BodyKind.OBJECT:
                return "OBJECT"

    def get_blender_size(self) -> tuple:
        return (
            self.size[0],
            self.size[1],
            self.size[2],
        )

class FieldKind(Enum):
    INTEGER = 0
    DECIMAL = 1
    BOOLEAN = 2
    STRING  = 3
    SWITCH  = 4
    VECTOR  = 5
    INDEX   = 6

@dataclass(init=False)
class Field:
    name: str
    info: str
    kind: FieldKind
    data: int | float | bool | str | list

    def __init__(self, key: str, value: dict):
        value = Reader(value, "Field")

        self.name = value_or_default(value, "name", key)
        self.info = value_or_default(value, "info", "No info.")

        match value_or_default(value, "kind", "integer"):
            case "integer":
                self.kind = FieldKind.INTEGER
                self.data = value_or_default(value, "data", 0)
            case "decimal":
                self.kind = FieldKind.DECIMAL
                self.data = value_or_default(value, "data", 0.0)
            case "boolean":
                self.kind = FieldKind.BOOLEAN
                self.data = value_or_default(value, "data", False)
            case "string":
                self.kind = FieldKind.STRING
                self.data = value_or_default(value, "data", "")
            case "switch":
                list = value["list"]
                self.kind = FieldKind.SWITCH
                self.data = value["data"]
                self.list = []

                for value in list:
                    self.list.append((
                        value[0],
                        value[1],
                        value[2],
                    ))
            case "vector":
                type      = value_or_default(value, "type", "xyz")
                self.kind = FieldKind.VECTOR
                self.data = tuple(value_or_default(value, "data", [0, 0, 0]))

                if type in ["xyz", "translation", "direction", "velocity", "euler", "quaternion", "color"]:
                    self.type = type.upper()
                else:
                    value_error("type", type, ["xyz", "translation", "direction", "velocity", "euler", "quaternion", "color"])
            case "index":
                self.kind = FieldKind.INDEX
            case x:
                value_error("kind", x, ["integer", "decimal", "boolean", "switch", "string", "vector", "color", "index"])

    def get_blender_property(self):
        match self.kind:
            case FieldKind.INTEGER:
                return bpy.props.IntProperty(
                    name        = self.name,
                    description = self.info,
                    default     = self.data
                )
            case FieldKind.DECIMAL:
                return bpy.props.FloatProperty(
                    name        = self.name,
                    description = self.info,
                    default     = self.data
                )
            case FieldKind.BOOLEAN:
                return bpy.props.BoolProperty(
                    name        = self.name,
                    description = self.info,
                    default     = self.data
                )
            case FieldKind.STRING:
                return bpy.props.StringProperty(
                    name        = self.name,
                    description = self.info,
                    default     = self.data
                )
            case FieldKind.SWITCH:
                return bpy.props.EnumProperty(
                    name        = self.name,
                    description = self.info,
                    default     = self.data,
                    items       = self.list
                )
            case FieldKind.VECTOR:
                return bpy.props.FloatVectorProperty(
                    name        = self.name,
                    description = self.info,
                    default     = self.data,
                    subtype     = self.type
                )
            case FieldKind.INDEX:
                return bpy.props.PointerProperty(
                    name        = self.name,
                    description = self.info,
                    type        = bpy.types.Object
                )

@dataclass(init=False)
class Entity:
    name: str
    info: str
    body: Body
    field: [Field]

    def __init__(self, key: str, value: dict):
        value = Reader(value, "Entity")

        self.name  = value_or_default(value, "name", key)
        self.info  = value_or_default(value, "info", "No info.")
        self.body  = Body(value_or_default(value, "body", {}))
        self.field = {}

        field = value_or_default(value, "field", {})

        for key, value in field.items():
            self.field[key] = Field(key, value)

@dataclass(init=False)
class Editor:
    BLENDER_UP_VECTOR = Vector((0, 0, 1))

    up                : [float]
    always_initialize : bool

    def __init__(self, value: dict):
        value = Reader(value, "Editor")

        up = value_or_default(value, "up", [0, 1, 0])

        self.up = Vector((
            up[0],
            up[1],
            up[2]
        ))
        self.always_initialize = value_or_default(value, "always_initialize", True)

    def user_to_blender_vector(self, value: Vector) -> Vector:
        return self.up.rotation_difference(self.BLENDER_UP_VECTOR) @ value

    def blender_to_user_vector(self, value: Vector) -> Vector:
        return self.BLENDER_UP_VECTOR.rotation_difference(self.up) @ value

@dataclass(init=False)
class Meta:
    editor: Editor
    object: dict[str, Field]
    entity: dict[str, Entity]

    def __init__(self, value: dict):
        value = Reader(value, "Meta")

        editor = value_or_default(value, "editor", {})
        object = value_or_default(value, "object", {})
        entity = value_or_default(value, "entity", {})

        self.editor = Editor(editor)
        self.object = {}
        self.entity = {}

        for key, value in object.items():
            self.object[key] = Field(key, value)

        for key, value in entity.items():
            self.entity[key] = Entity(key, value)

class Reader:
    def __init__(self, value: dict, trace: str):
        self.value = value
        self.trace = trace

    def __contains__(self, index):
        if index in self.value:
            return True
        else:
            return False

    def __getitem__(self, index):
        if index in self.value:
            return self.value[index]
        else:
            structure = self.trace
            raise KeyError(f"Non-existent key \"{index}\" for structure \"{structure}\".")