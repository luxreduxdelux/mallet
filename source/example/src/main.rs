/*
* ================================================================
* This is a very basic example of using Mallet for exporting a .GLB file and loading it in
* a custom game engine.
* When we have to load a level, we load the GLTF data in memory and iterate over each node,
* checking if it has an extra data payload or not.
* If it does, we extract the payload and deserialize it, and spawn the appropiate entity.
* You might want to keep a HashMap registry tracking an entity's "class name" with a spawn
* function, or write a macro to automatically derive it.
* This example is also a show-case of the Game Launch feature in Mallet; exporting and immediately
* launching the game after, even passing along the view-port camera's location and
* rotation into the game.
* If you launch the game through Blender, it will listen for any modification to the level file
* and automatically re-load the level.
* ================================================================
*/

use notify::{Config, Event, INotifyWatcher, RecommendedWatcher, RecursiveMode, Watcher};
use raylib::prelude::*;
use std::collections::HashMap;
use std::path::Path;
use std::sync::mpsc::Receiver;
use std::sync::mpsc::channel;

//================================================================

fn main() {
    // Create Raylib context.
    let (mut handle, thread) = raylib::init()
        .size(1024, 768)
        .log_level(TraceLogLevel::LOG_NONE)
        .resizable()
        .title("Mallet - Example")
        .build();
    handle.set_target_fps(60);

    // Handle loading a level on disk if we got it as an environment variable.
    let mut level: Option<Level> = if let Some(path) = get_launch_level() {
        match Level::new(&mut handle, &thread, &path) {
            Ok(ok) => Some(ok),
            Err(error) => {
                println!("{error:#?}");
                None
            }
        }
    } else {
        None
    };

    // Set up a file-modification listener.
    let listen = if let Some(path) = get_launch_level()
        && let Ok(rx) = listen_for_file(&path)
    {
        Some(rx)
    } else {
        None
    };

    // Handle obtaining the view-port camera from Blender if we got it as an environment variable.
    let camera = get_launch_camera();

    while !handle.window_should_close() {
        // Handle file dropping.
        if handle.is_file_dropped()
            && let Some(path) = handle.load_dropped_files().paths().first()
        {
            match Level::new(&mut handle, &thread, path) {
                Ok(ok) => {
                    level = Some(ok);
                }
                Err(error) => println!("{error:#?}"),
            }
        }

        // Handle listening for level modification.
        if let Some((_, listen)) = &listen {
            while let Ok(path) = listen.try_recv() {
                match Level::new(&mut handle, &thread, &path) {
                    Ok(ok) => {
                        level = Some(ok);
                    }
                    Err(error) => println!("{error:#?}"),
                }
            }
        }

        //================================================================
        // 2D draw.
        //================================================================

        let mut draw = handle.begin_drawing(&thread);

        draw.clear_background(Color::WHITE);

        if let Some(l) = &level {
            draw.draw_text("Press F1 to re-load the level.", 8, 8, 30, Color::BLACK);

            // Draw entity data from the level.
            for (i, entity) in l.entity.iter().enumerate() {
                let text = entity.text();

                draw.draw_text(
                    &format!("Entity {i}: {text}"),
                    8,
                    30 * (i as i32 + 1) + 5,
                    30,
                    Color::BLACK,
                );
            }

            // Handle level re-loading.
            if draw.is_key_pressed(KeyboardKey::KEY_F1) {
                match Level::new(&mut draw, &thread, &l.level) {
                    Ok(ok) => {
                        level = Some(ok);
                    }
                    Err(error) => println!("{error:#?}"),
                }
            }
        } else {
            draw.draw_text(
                "Drag and drop a .GLB file onto the window.",
                8,
                8,
                30,
                Color::BLACK,
            );
        }

        //================================================================
        // 3D draw.
        //================================================================

        let mut draw = draw.begin_mode3D(camera);

        draw.draw_grid(32, 1.0);

        if let Some(level) = &level {
            draw.draw_model(&level.model, Vector3::zero(), 1.0, Color::WHITE);

            for entity in &level.entity {
                entity.draw(&mut draw);
            }
        }
    }
}

//================================================================

struct Level {
    level: String,
    model: Model,
    entity: Vec<Entity>,
}

impl Level {
    fn new(handle: &mut RaylibHandle, thread: &RaylibThread, path: &str) -> anyhow::Result<Self> {
        let model = handle.load_model(thread, path)?;
        let file = std::fs::read(path)?;
        let gltf = gltf::Gltf::from_slice(&file)?;
        let mut entity = Vec::default();

        for scene in gltf.scenes() {
            for node in scene.nodes() {
                if let Some(extra) = node.extras() {
                    let extra = extra.get();
                    let extra: HashMap<String, serde_json::Value> = serde_json::from_str(extra)?;

                    println!("GLTF extra data: {extra:#?}");

                    if let Some(entity_index) = extra.clone().get("entity_index")
                        && let serde_json::Value::String(index) = entity_index
                    {
                        entity.push(Entity::new(
                            index,
                            EntityData::new(node.transform()),
                            extra,
                        )?);
                    }
                }
            }
        }

        Ok(Self {
            level: path.to_string(),
            model,
            entity,
        })
    }
}

//================================================================

enum Entity {
    Cube {
        e_data: EntityData,
        c_data: CubeData,
    },
    Sphere {
        e_data: EntityData,
        s_data: SphereData,
    },
}

impl Entity {
    fn new(
        index: &str,
        e_data: EntityData,
        value: HashMap<String, serde_json::Value>,
    ) -> anyhow::Result<Self> {
        match index {
            "entity_cube" => {
                if let Some(value) = value.get("entity_cube")
                    && let Ok(c_data) = serde_json::from_value(value.clone())
                {
                    return Ok(Self::Cube { e_data, c_data });
                }
            }
            _ => {
                if let Some(value) = value.get("entity_sphere")
                    && let Ok(s_data) = serde_json::from_value(value.clone())
                {
                    return Ok(Self::Sphere { e_data, s_data });
                }
            }
        }

        anyhow::bail!(format!(
            "Error creating entity with entity data: {value:#?}."
        ));
    }

    fn draw(&self, draw: &mut RaylibMode3D<'_, RaylibDrawHandle<'_>>) {
        match self {
            Entity::Cube { e_data, c_data } => {
                draw.draw_cube_v(e_data.point, Vector3::ONE * c_data.scale, Color::RED);
            }
            Entity::Sphere { e_data, s_data } => {
                draw.draw_sphere(e_data.point, s_data.scale, Color::GREEN);
            }
        }
    }

    fn text(&self) -> String {
        match self {
            Entity::Cube { e_data, c_data } => {
                format!("Point: {:?}, Scale: {}", e_data.point, c_data.scale)
            }
            Entity::Sphere { e_data, s_data } => {
                format!("Point: {:?}, Scale: {}", e_data.point, s_data.scale)
            }
        }
    }
}

struct EntityData {
    point: Vector3,
}

impl EntityData {
    fn new(transform: gltf::scene::Transform) -> Self {
        let (translation, _, _) = transform.decomposed();

        Self {
            point: Vector3::new(translation[0], translation[1], translation[2]),
        }
    }
}

#[derive(serde::Deserialize)]
struct CubeData {
    scale: f32,
}

#[derive(serde::Deserialize)]
struct SphereData {
    scale: f32,
}

//================================================================

fn get_launch_level() -> Option<String> {
    if let Ok(level) = std::env::var("MALLET_LEVEL") {
        Some(level)
    } else {
        None
    }
}

fn get_launch_camera() -> Camera3D {
    let point = if let Ok(Some(point)) = get_vector("MALLET_POINT") {
        point
    } else {
        Vector3::ONE * 8.0
    };

    Camera3D::perspective(point, Vector3::ZERO, Vector3::Y, 40.0)
}

fn get_vector(key: &str) -> anyhow::Result<Option<Vector3>> {
    if let Ok(x) = std::env::var(format!("{key}_X"))
        && let Ok(y) = std::env::var(format!("{key}_Y"))
        && let Ok(z) = std::env::var(format!("{key}_Z"))
    {
        Ok(Some(Vector3::new(x.parse()?, y.parse()?, z.parse()?)))
    } else {
        Ok(None)
    }
}

fn listen_for_file(path: &str) -> anyhow::Result<(INotifyWatcher, Receiver<String>)> {
    let (tx, rx) = channel();

    let mut watcher = RecommendedWatcher::new(
        move |event: notify::Result<Event>| {
            if let Ok(event) = event
                && let notify::EventKind::Modify(_) = event.kind
                && let Some(path) = event.paths.first()
            {
                tx.send(path.display().to_string()).unwrap();
            }
        },
        Config::default(),
    )?;

    watcher.watch(Path::new(path), RecursiveMode::NonRecursive)?;

    println!("Listening for file {path:#?}");

    Ok((watcher, rx))
}
