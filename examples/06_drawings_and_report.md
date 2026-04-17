# Drawings and a project report

From a finished model to a dimensioned 2D drawing plus a Markdown
project report in one session.

## Drawings

```text
# Create a TechDraw page (uses bundled A4 landscape template by default)
create_drawing_page name=Assembly_Sheet1

# Standard three-view + iso
add_drawing_view page_name=Assembly_Sheet1 source_objects=[AssemblyRoot] view_type=Front scale=0.5
add_drawing_view page_name=Assembly_Sheet1 source_objects=[AssemblyRoot] view_type=Top   scale=0.5
add_drawing_view page_name=Assembly_Sheet1 source_objects=[AssemblyRoot] view_type=Right scale=0.5
add_drawing_view page_name=Assembly_Sheet1 source_objects=[AssemblyRoot] view_type=Iso   scale=0.4

# Dimension an edge in the front view
add_drawing_dimension \
  view_name=Assembly_Sheet1_Front \
  kind=Distance \
  refs=[{"subname":"Vertex1"},{"subname":"Vertex3"}]

# Export
export_drawing_pdf page_name=Assembly_Sheet1 path="C:/out/assembly_sheet1.pdf"
export_drawing_svg page_name=Assembly_Sheet1 path="C:/out/assembly_sheet1.svg"
```

## Report

```text
# Assigns and BC tags are picked up automatically
generate_report \
  output_dir="C:/out/assembly_report" \
  title="Assembly v1.0 — design review" \
  render_views=["Isometric","Front","Top","Right"] \
  author="L. Salvador"
```

The output directory contains:

```
report.md
view_isometric.png
view_front.png
view_top.png
view_right.png
```

Convert to PDF with pandoc if desired:

```bash
pandoc report.md -o report.pdf --pdf-engine=xelatex
```

## Document diff

If you have two revisions of the same file, compare them:

```text
compare_documents \
  a_path="C:/archive/assembly_v0.9.FCStd" \
  b_path="C:/out/assembly_v1.0.FCStd"
```

Output lists objects added, removed, and changed (with delta on
volume, area, bounding box, material assignment, and BC tags).
