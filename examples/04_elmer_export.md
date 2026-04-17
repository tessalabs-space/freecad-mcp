# Elmer export with BC tags

Shows how BC tags added with `tag_faces` / `tag_boundary_by_normal`
flow through to an Elmer `.sif` case.

```text
# Assume Housing is a simplified body.
assign_material obj_name=Housing material=Aluminum_6061_T6

# Tag the outward-facing panel as a heat source
tag_boundary_by_normal obj_name=Housing tag=heat_source direction={x:0,y:0,z:1}

# Fixed-temperature radiator face on the opposite side
tag_boundary_by_normal obj_name=Housing tag=radiator direction={x:0,y:0,z:-1} \
  tolerance_deg=10

list_bc_tags obj_name=Housing

# Export. The exporter reads the material metadata and creates
# ObjectsFem.makeConstraintTemperature for each BC tag.
export_elmer output_dir="C:/sim/housing_thermal" \
  objects=[Housing] analysis=HeatTransfer mesh_size_mm=2
```

In the output directory you will find the mesh input (`case.unv`) and
the Elmer SIF. Run externally:

```bash
cd C:/sim/housing_thermal
ElmerSolver case.sif
```

Post-process with ParaView against `case.vtu`.
