# Simplify a CAD import for thermal analysis

You received a STEP file from mechanical. It has every bolt, screw,
fillet, and M3 clearance hole. For a steady-state thermal run, almost
all of that is irrelevant and will make the mesh 10× larger than it
needs to be. Here is the canonical clean-up:

```text
import_file path="C:/cad/payload_assembly.step" doc_name=Payload

# Inventory first — never destructive straight away.
get_objects doc_name=Payload
find_fasteners doc_name=Payload
find_holes obj_name=Housing max_diameter=6
find_fillets obj_name=Housing max_radius=2

# Remove fasteners (dry_run first!)
remove_fasteners doc_name=Payload dry_run=true
# Looks right? Commit.
remove_fasteners doc_name=Payload dry_run=false

# Strip small features on the main housing
remove_holes obj_name=Housing max_diameter=6 name=Housing_step1
remove_fillets obj_name=Housing_step1 max_radius=2 name=Housing_clean

# Keep only the outer shell for radiation analysis
keep_external_surfaces obj_name=Housing_clean name=Housing_shell

# Exploit symmetry if present
detect_symmetry obj_name=Housing_clean

# Now assign materials and tag BCs
list_materials
assign_material obj_name=Housing_clean material=Aluminum_6061_T6
tag_boundary_by_normal obj_name=Housing_clean tag=radiator direction={x:0,y:0,z:1}
tag_boundary_by_normal obj_name=Housing_clean tag=wall direction={x:0,y:0,z:-1}

# Ship to Elmer
export_elmer output_dir="C:/sim/payload_thermal" objects=[Housing_clean] analysis=HeatTransfer mesh_size_mm=3
```

For the final cinematic render, hand off to Blender:

```text
export_for_blender output_dir="C:/sim/payload_render"
```

The sidecar `scene.json` carries material properties and the radiator /
wall face groups so the Blender MCP can apply PBR materials and create
named collections automatically.
