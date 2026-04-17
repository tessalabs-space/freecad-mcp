# Parametric sweep

Two ways to explore design variations: drive a single property on one
object, or drive a spreadsheet cell that fans out through expressions.

## Single-property sweep

Say you have a cylindrical tank and you want to know mass at five
different lengths, exported as STEP files.

```text
create_document name=Tank
create_primitive kind=cylinder name=TankBody properties={"Radius": 40, "Height": 120}
assign_material obj_name=TankBody material=Stainless_Steel_304

parametric_sweep \
  obj_name=TankBody \
  property_name=Height \
  values=[80, 100, 120, 140, 160] \
  export_dir="C:/sweeps/tank_length" \
  export_format=step \
  capture_mass=true \
  capture_screenshot=true
```

Returns a table:

```json
{
  "rows": [
    {"value": 80,  "volume_mm3": 402123.9, "surface_area_mm2": 30159.3,
     "path": "C:/sweeps/tank_length/TankBody_Height_80.step",
     "screenshot": "C:/sweeps/tank_length/TankBody_Height_80.png"},
    ...
  ]
}
```

Pair with `mass_budget` or `generate_report` for a quick trade study.

## Spreadsheet-driven sweep

When a single parameter feeds many objects through FreeCAD expressions
(common in well-parameterised models), drive the spreadsheet cell
instead:

```text
spreadsheet_sweep \
  spreadsheet_name=DesignParams \
  cell=B2 \
  values=[10, 15, 20, 25] \
  export_dir="C:/sweeps/wall_thickness" \
  export_format=stl
```

Every downstream object that binds to `DesignParams.B2` updates at each
step.
