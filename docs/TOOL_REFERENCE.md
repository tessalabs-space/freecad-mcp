# Tool reference

Every tool on the MCP server maps one-to-one to an addon RPC handler.
This is the surface, grouped by intent.

## Documents

| Tool | Purpose |
| --- | --- |
| `create_document(name)` | New empty document |
| `list_documents()` | Names of open docs |
| `open_document(path)` | Open `.FCStd` |
| `save_document(doc_name?, path?)` | Save in place or save-as |
| `close_document(doc_name)` | Close without save |
| `recompute(doc_name?)` | Force dependency recompute |
| `get_objects(doc_name?)` | Type + visibility of every object |
| `get_object(obj_name, doc_name?)` | Full properties dump |
| `delete_object(obj_name, doc_name?)` | Remove + recompute |
| `rename_object(obj_name, new_label, doc_name?)` | Change an object's Label (collisions auto-suffixed) |
| `rename_objects(renames, doc_name?)` | Batch rename via `[{name, label}, ...]` — cleanup pass after STEP imports |

## Geometry

| Tool | Purpose |
| --- | --- |
| `create_primitive(kind, name, properties?, doc_name?)` | box, cylinder, sphere, cone, torus, plane, wedge, ellipsoid, prism |
| `boolean_op(op, bases, tools, ...)` | fuse, cut, common, intersection |
| `fillet(obj, edges, radius)` | Constant-radius fillet on edge indices |
| `chamfer(obj, edges, size)` | Constant-size chamfer |
| `thickness(obj, faces, value, mode?)` | Hollow a solid |
| `mirror(obj, base, normal)` | Mirror across a plane |
| `translate(obj, delta)` / `rotate(obj, axis, angle, center?)` | Placement transforms |

## Sketch + Part

`create_sketch`, `sketch_add_line`, `sketch_add_circle`,
`sketch_add_rectangle`, `sketch_add_constraint`. Then `extrude`,
`revolve`, `loft`, `sweep`.

## Import / export

| Tool | Purpose |
| --- | --- |
| `import_file(path, doc_name?)` | STEP, IGES, STL, BREP, OBJ, FCStd |
| `export_file(path, object_names?, tolerance_report?)` | Same formats, with optional round-trip bbox diff |
| `audit_units(doc_name?)` | Report doc unit system |

## Defeaturing

| Tool | Purpose |
| --- | --- |
| `find_holes`, `remove_holes` | Cylindrical holes by diameter |
| `find_fillets`, `remove_fillets` | Cylindrical / toroidal fillet faces by radius |
| `remove_chamfers` | Narrow planar bands |
| `find_fasteners`, `remove_fasteners` | By label pattern AND shape fingerprint. Default `dry_run=true` |
| `find_thin_bodies` | Flag sub-threshold bounding boxes |

## Shape healing / simplification

Generic OCC repairs for imported geometry — use before meshing or feature-specific defeaturing.

| Tool | Purpose |
| --- | --- |
| `simplify_shape(obj_name, remove_splitter?, unify_faces?, unify_edges?, heal?, sew_tolerance_mm?, min_face_area_mm2?)` | Pipelined heal → splitter → unify-same-domain → optional sew → optional tiny-face drop |
| `find_small_faces(obj_name, max_area_mm2?)` | List faces under an area threshold |
| `remove_small_faces(obj_name, max_area_mm2?)` | Drop those faces via `removeFeature` |

## Analysis prep

`extract_midsurface`, `detect_symmetry`, `keep_external_surfaces`,
`find_contact_faces`, `imprint_merge`.

## Materials

`list_materials`, `get_material`, `assign_material`,
`get_assigned_material`. The library lives at
`addon/FreeCADMCP/libs/materials.json`; extend it in place.

## BC tagging

`list_bc_tags`, `tag_faces`, `untag_faces`, `tag_boundary_by_normal`.

Standard tag vocabulary: `inlet`, `outlet`, `wall`, `symmetry`,
`radiator`, `heat_source`, `heat_sink`, `fixture`, `load`, `contact`,
`interface`, `free_surface`, `periodic`. Others auto-prefix with
`custom:`.

## Inspection

`mass_properties`, `clash_detection`, `distance_between`,
`expression_report`.

## Annotations / views

`add_callout`, `add_dimension`, `clear_annotations`, `set_view`,
`screenshot`, `section_cut`, `explode`.

## Animation / render

| Tool | Purpose |
| --- | --- |
| `turntable(output_dir, frames?, axis?, ...)` | 360° camera orbit → PNG sequence |
| `keyframe_camera(output_dir, keyframes, frames_between?, ...)` | Interpolated camera path → PNG sequence |
| `keyframe_parts(output_dir, tracks, frames_between?, ...)` | Animate object Placements (pos + axis-angle rotation) across keyframes → PNG sequence; original placements restored after render |
| `render_png(path?, width?, height?, background?, quality?)` | One high-quality still |
| `encode_video(frames_dir, output_path, fps?, pattern?, crf?)` | Encode PNG frames to mp4 / webm / gif / mov via ffmpeg (ffmpeg must be on PATH) |
| `ffmpeg_available(ffmpeg_path?)` | Probe whether ffmpeg is reachable |

## Meshing

Standalone Gmsh meshing + neutral-format mesh export, independent of the full solver-deck writers below.

| Tool | Purpose |
| --- | --- |
| `generate_mesh(obj_name, mesh_size_mm?, min_size_mm?, order?, algorithm_2d?, algorithm_3d?)` | Build a `FemMeshGmsh` on a Part/Shape (order 1 linear, 2 quadratic); returns node / element counts |
| `list_meshes(doc_name?)` | Enumerate FEM meshes and surface meshes in the document |
| `export_mesh(mesh_name, path)` | Write to `.unv`, `.inp`, `.med`, `.vtk`, `.dat`, `.bdf`, `.z88` (FEM) or `.stl`, `.obj`, `.ply` (surface) — extension picks format |

## Solver export

`export_elmer(output_dir, objects, analysis?, mesh_size_mm?)`,
`export_calculix(output_dir, objects, mesh_size_mm?)`,
`export_openfoam_stl(output_dir, objects)`.

## Blender bridge

`export_for_blender(output_dir, objects?, doc_name?)` writes
`scene.glb` + `scene.json` with material + BC metadata.

## Parametric studies

| Tool | Purpose |
| --- | --- |
| `parametric_sweep(obj, property, values, export_dir?, export_format?, capture_mass?, capture_screenshot?)` | Iterate a property through values; export + record per step |
| `spreadsheet_sweep(spreadsheet, cell, values, export_dir?, export_format?)` | Drive an expression-linked spreadsheet cell |

## Reporting + budgeting

| Tool | Purpose |
| --- | --- |
| `generate_report(output_dir, title, sections?, render_views?, author?)` | Markdown project report with renders, object / material / BC / mass / clash tables |
| `mass_budget(doc_name?, default_density_kg_m3?, group_by_prefix?, grouping?)` | Per-object + aggregate mass and weighted CG |
| `compare_documents(a_path, b_path)` | Structural diff between two .FCStd files |

## Drawings (TechDraw)

| Tool | Purpose |
| --- | --- |
| `create_drawing_page(template_path?, name?)` | New TechDraw page (default template auto-located) |
| `add_drawing_view(page, sources, view_type, position?, scale?, show_hidden?)` | Orthographic (Front/Back/Top/Bottom/Left/Right) or Iso view |
| `add_drawing_dimension(view, kind, refs)` | Distance / DistanceX / DistanceY / Radius / Diameter / Angle |
| `export_drawing_pdf(page, path)` / `export_drawing_svg(page, path)` | Page export |

## Structural load cases

| Tool | Purpose |
| --- | --- |
| `create_modal_analysis(objects, mode_count?, mesh_size_mm?, fixture_face_tags?)` | CalculiX eigenmode |
| `create_static_acceleration_case(objects, accel_g, fixture_face_tags?, mesh_size_mm?)` | Quasi-static acceleration |
| `create_random_vibration_case(output_dir, objects, psd_x/y/z, fixture_face_tags?, q_factor?)` | Modal + PSD sidecar JSON |

## Particulate / DEM export

`export_for_dem(output_dir, objects, roughness_um?, friction_coefficient?, surface_energy_mJ_m2?, restitution_coefficient?)` — STL per object + `dem_manifest.json` consumed by Yade / LIGGGHTS / MFIX-style tools.

## Escape hatch

`execute_code(code)` — runs arbitrary Python inside the FreeCAD GUI
process. Prefer a typed tool when the pattern recurs.
