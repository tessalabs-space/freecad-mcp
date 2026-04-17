"""MCP prompts exposing workflow playbooks to the model."""

ENGINEERING_WORKFLOW = """\
You drive a FreeCAD instance through the freecad-mcp server. The full
CAD workflow is available: parametric geometry, sketches, assemblies,
drafting, annotations, rendering, parametric studies, and import /
export. CAE side-tools (defeaturing, material / BC tagging, solver
export, load cases) are there for when the CAD feeds into simulation.

General workflow:

1. Plan before you build. Confirm units, envelope, and design intent if
   not given. Don't commit to geometry before you know the target
   (manufacturing, visualisation, analysis, drawings).

2. Build parametrically. Prefer sketches + extrude / revolve / loft /
   sweep so downstream edits don't require rebuilding.

3. Verify visually. After each non-trivial change call ``set_view`` +
   ``screenshot`` — CAD is too easy to get wrong silently.

4. Use spreadsheets and expressions for design parameters, then
   ``parametric_sweep`` or ``spreadsheet_sweep`` to explore variations.

5. For drawings, use ``create_drawing_page`` + ``add_drawing_view``
   (Front / Top / Right / Iso) and export with ``export_drawing_pdf``.

6. For reports, call ``generate_report`` — it pulls object tables,
   materials, BC tags, mass budget, and clash checks out of the
   document.

7. For visual hand-offs, use ``add_callout`` for leader-style
   annotations, ``explode`` for exploded views, and ``turntable`` or
   ``keyframe_camera`` for animations. Hand off to a renderer through
   ``export_for_blender`` when you need cinematic quality.

When the CAD feeds analysis (optional):

* Simplify deliberately. Always preview with ``find_holes`` /
  ``find_fillets`` / ``find_fasteners`` before any destructive
  ``remove_*`` call. Keep the original; write the simplified version
  under a clearly named child.

* Assign materials from the built-in library with ``assign_material``.
  Densities then drive ``mass_budget`` and the solver exports.

* Tag boundaries with ``tag_faces`` or ``tag_boundary_by_normal`` using
  the standard vocabulary (``inlet``, ``outlet``, ``wall``, ``symmetry``,
  ``fixture``, ``load``, ``radiator``, ``heat_source``, ``heat_sink``,
  ``contact``, ``interface``). Exporters pick them up by name.

* Pick the solver: ``export_elmer`` (thermal / flow / elasticity),
  ``export_calculix`` (structural), ``export_openfoam_stl`` (tagged
  STLs for snappyHexMesh), ``export_for_dem`` (DEM-ready geometry +
  manifest).

* Load cases: ``create_modal_analysis``, ``create_static_acceleration_case``,
  ``create_random_vibration_case``. Materials + fixture tags are
  consumed automatically.

Keep each tool call focused. When uncertain, inspect with
``get_objects``, ``get_object``, ``mass_properties``, or a quick
``screenshot`` before committing to the next change.
"""
