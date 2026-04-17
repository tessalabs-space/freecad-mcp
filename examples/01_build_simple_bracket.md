# Build a simple bracket

A parametric L-bracket with mounting holes. Shows the minimum useful
path through sketch → extrude → holes → fillets.

```text
create_document name=Bracket

# Sketch the L profile on XY
create_sketch name=Profile plane=XY doc_name=Bracket

sketch_add_rectangle sketch_name=Profile origin={x:0,y:0} width=80 height=20
sketch_add_rectangle sketch_name=Profile origin={x:0,y:0} width=20 height=60

# Extrude 5 mm
extrude profile=Profile length=5 doc_name=Bracket name=BracketBody

# Four M4 holes, clearance 4.2 mm
create_sketch name=HolePattern plane=XY doc_name=Bracket
sketch_add_circle sketch_name=HolePattern center={x:10,y:10} radius=2.1
sketch_add_circle sketch_name=HolePattern center={x:70,y:10} radius=2.1
sketch_add_circle sketch_name=HolePattern center={x:10,y:50} radius=2.1
sketch_add_circle sketch_name=HolePattern center={x:10,y:30} radius=2.1
extrude profile=HolePattern length=5 doc_name=Bracket name=HoleSolid

boolean_op op=cut bases=[BracketBody] tools=[HoleSolid] name=Bracket_Final

# Break the sharp corners
fillet obj_name=Bracket_Final edges=[3,4,7,8] radius=2

set_view direction=Isometric focus_object=Bracket_Final
screenshot
```

Every step is live — edit the sketch values, call `recompute`, and the
model updates.
