# Render with callouts and turntable

The movie-style render: beautiful orbit, labelled components, clean
background. Example assembly names are placeholders — swap them for
whatever your document actually contains.

```text
# Position the view
set_view direction=Isometric focus_object=AssemblyRoot

# Leader arrows to each named part
add_callout label="Top cover" target_object=TopCover target_face=3 \
  offset={x:60,y:40,z:60} color=[0.95, 0.75, 0.20]

add_callout label="Main board" target_object=MainBoard \
  offset={x:-80,y:0,z:40} color=[0.30, 0.90, 0.40]

add_callout label="Mounting bracket" target_object=Bracket target_face=1 \
  offset={x:0,y:80,z:20} color=[0.90, 0.30, 0.30]

# Single hero shot
render_png path="C:/renders/hero.png" width=3840 height=2160 quality=high

# 6-second turntable at 30 fps = 180 frames
turntable output_dir="C:/renders/turntable" frames=180 axis=Z width=1920 height=1080

# Strip the callouts before the next pass
clear_annotations
```

Combine the frames externally:

```bash
ffmpeg -r 30 -i C:/renders/turntable/frame_%04d.png -c:v libx264 -pix_fmt yuv420p turntable.mp4
```

For cinematic quality, hand off to Blender instead of rendering in
FreeCAD:

```text
export_for_blender output_dir="C:/renders/blender_scene"
```

The sidecar `scene.json` carries materials and any BC tags so a
companion Blender MCP can apply PBR shaders and create named
collections automatically.
