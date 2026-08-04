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

@dataclass(init=False)
class Name:
    internal: str
    external: str

    def __init__(self, value: dict):
        value = Reader(value, "Name")

        self.internal = value["internal"]
        self.external = value["external"]

class BodyKind(Enum):
    AXIS   = 0
    CUBOID = 1
    SPHERE = 2
    MODEL  = 3

@dataclass(init=False)
class Body:
    kind: BodyKind
    data: Vector

    def __init__(self, value: dict):
        value = Reader(value, "Body")

        match value["kind"]:
            case "axis":
                self.kind = BodyKind.AXIS
            case "cuboid":
                self.kind = BodyKind.CUBOID
                self.size = Vector((
                    value["size"][0],
                    value["size"][1],
                    value["size"][2]
                ))
            case "sphere":
                self.kind = BodyKind.SPHERE
                self.size = Vector((
                    value["size"][0],
                    value["size"][1],
                    value["size"][2]
                ))
            case "model":
                self.kind = BodyKind.MODEL
            case x:
                value_error("body", x, ["axis", "cuboid", "sphere", "model"])

    def get_blender_body(self) -> str:
        match self.kind:
            case BodyKind.AXIS:
                return "PLAIN_AXIS"
            case BodyKind.CUBOID:
                return "CUBE"
            case BodyKind.SPHERE:
                return "SPHERE"
            case BodyKind.MODEL:
                return "MODEL"

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
    SWITCH  = 3
    STRING  = 4
    VECTOR  = 5
    COLOR   = 6
    INDEX   = 7

@dataclass(init=False)
class Field:
    name: Name
    info: str
    kind: FieldKind
    data: int | float | bool | str | list

    def __init__(self, value: dict):
        value = Reader(value, "Field")

        self.name = Name(value["name"])
        self.info = value["info"]

        match value["kind"]:
            case "integer":
                self.kind = FieldKind.INTEGER
                self.data = value["data"]
            case "decimal":
                self.kind = FieldKind.DECIMAL
                self.data = value["data"]
            case "boolean":
                self.kind = FieldKind.BOOLEAN
                self.data = value["data"]
            case "switch":
                self.kind = FieldKind.SWITCH
                self.data = value["data"]
            case "string":
                self.kind = FieldKind.STRING
                self.data = value["data"]
            case "vector":
                self.kind = FieldKind.VECTOR
                self.data = value["data"]
            case "color":
                self.kind = FieldKind.COLOR
                self.data = value["data"]
            case "index":
                self.kind = FieldKind.INDEX
            case x:
                value_error("kind", x, ["integer", "decimal", "boolean", "switch", "string", "vector", "color", "index"])

    def get_blender_property(self):
        match self.kind:
            case FieldKind.INTEGER:
                return bpy.props.IntProperty(
                    name        = self.name.internal,
                    description = self.info,
                    default     = self.data
                )
            case FieldKind.DECIMAL:
                return bpy.props.FloatProperty(
                    name        = self.name.internal,
                    description = self.info,
                    default     = self.data
                )
            case FieldKind.STRING:
                return bpy.props.StringProperty(
                    name        = self.name.internal,
                    description = self.info,
                    default     = self.data
                )
            case _:
                ...

@dataclass(init=False)
class Entity:
    name: Name
    info: str
    body: Body
    field: [Field]

    def __init__(self, value: dict):
        value = Reader(value, "Entity")

        self.name  = Name(value["name"])
        self.info  = value["info"]
        self.body  = Body(value["body"])
        self.field = []

        for field in value["field"]:
            self.field.append(Field(field))

@dataclass(init=False)
class Editor:
    BLENDER_UP_VECTOR = Vector((0, 0, 1))

    up: [float]
    path: str

    def __init__(self, value: dict):
        value = Reader(value, "Editor")

        self.up = Vector((
            value["up"][0],
            value["up"][1],
            value["up"][2]
        ))
        self.path = value_or_default(value, "path", "")

    def user_to_blender_vector(self, value: Vector) -> Vector:
        return self.up.rotation_difference(self.BLENDER_UP_VECTOR) @ value

    def blender_to_user_vector(self, value: Vector) -> Vector:
        return self.BLENDER_UP_VECTOR.rotation_difference(self.up) @ value

@dataclass(init=False)
class UserFile:
    editor: Editor
    entity: [Entity]

    def __init__(self, value: dict):
        value = Reader(value, "UserFile")

        self.editor = Editor(value["editor"])
        self.entity = []

        for entity in value["entity"]:
            self.entity.append(Entity(entity))

    def get_entity_from_index(self, index: int) -> Entity:
        if index >= 0 and index < len(self.entity):
            return self.entity[index]

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