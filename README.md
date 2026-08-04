## Mallet
Mallet is a Blender add-on for game engine agnostic entity editing. You can create a level entirely in Blender and either export it with as a GLTF/GLB, or export the entity data in JSON format.

## Usage
### Interface
...

### Meta File
The meta file is a JSON file containing meta-data about every class of entity in your game as well as other miscellaneous editor data.

You must load this file before being able to access Mallet's entity editor.

```
{
    # Editor meta-data.
    "editor": {
        # Up vector. When parsing a vector from this file, it will use this vector to translate to Blender's Z-up vector and vice-versa.
        "up": [0.0, 1.0, 0.0],

        "export": {
            "location": "point",
            "rotation": "angle",
            "scale":    "scale"
        },

        # [OPTIONAL] Game directory. This is otherwise set by the "Select Game" button in Mallet, but may be set here for ease of use.
        "path": ""
    },

    # Entity array.
    "entity": [
        {
            # Entity name.
            "name": {
                # Entity name for use with Blender.
                "internal": "Player",

                # Entity name for use with your engine.
                "external": "entity_player"
            },

            # Entity info.
            "info": "Player spawn-point.",

            # Entity body.
            "body": {
                # Entity body kind. May be one of "axis", "cuboid", "sphere", or "model".
                "kind": "cuboid",

                # Entity body size. [OPTIONAL] for "model" body kind.
                "size": [0.5, 1.0, 0.5]
            },

            # Entity field array.
            "field": [
                {
                    # Field name.
                    "name": {
                        # Field name for use with Blender.
                        "internal": "Integer",

                        # Field name for use with your engine.
                        "external": "integer"
                    },

                    # Field info.
                    "info": "Integer.",

                    # Field kind. May be one of "integer", "decimal", "boolean", "switch", "string", "vector", "color", or "index".
                    "kind": "integer",

                    # Field data.
                    "data": 100
                },
                {
                    "name": {
                        "internal": "Decimal",
                        "external": "decimal"
                    },
                    "info": "Decimal.",
                    "kind": "decimal",
                    "data": 100.0
                },
                {
                    "name": {
                        "internal": "String",
                        "external": "string"
                    },
                    "info": "String.",
                    "kind": "string",
                    "data": "foo"
                }
            ]
        }
    ]
}
```

### Import/Export
...

### Launch Game
...

### Torch Integration
Mallet has integration with [Torch](https://github.com/luxreduxdelux/torch) and can bake before exporting using Torch's configuration or bake before launching the game.

It will automatically detect if Torch is available to use, so all you need to do is just install Torch.

## Example
You can find a working example of a Mallet meta-file and a basic game written in Rust that can read the GLB file with the Blender-written entity data in the [example](https://github.com/luxreduxdelux/mallet/tree/main/source/example) folder.

## Check Out...
[Torch](https://github.com/luxreduxdelux/torch), a one-click light-map bake add-on for Blender.

[Anvil](https://github.com/alexjhetherington/anvil-level-design), a Trenchbroom-like level design add-on for Blender.

## License
Mallet has a BSD-2-Clause-Patent license.