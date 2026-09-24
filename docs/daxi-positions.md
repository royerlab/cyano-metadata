# DaXi positions and room coordinates

This page explains how the position fields in a DaXi `.zattrs["daxi"]` block relate to the stored image arrays and to
the room, and how to turn the top and bottom objective positions into a vertical offset between the top and bottom
views.

The conversion rule below matches one hand-verified top/bottom alignment and is consistent with a second dataset.
Treat it as a working rule until more calibrations confirm it (see [Open questions](#open-questions)).

## Quick answer

The vertical offset between what the top and bottom objectives see is approximately the difference of their reported
positions:

```
vertical offset (um)   ~= top_objective_z_um - bottom_objective_z_um
vertical offset (rows) ~= vertical offset (um) / vertical um per camera row      (about 0.13 um per row)
```

`objective_position_offset_um` does not enter this rule, and neither does `estimated_volume_offset_um`.

```python
from cyano_metadata.daxi.v0_3 import load_daxi_metadata

VERTICAL_UM_PER_ROW = 0.1842 * 2**-0.5  # 45 degree sheet; see "Open questions"


def objective_z(meta, position):
    """(top, bottom) objective z in um for one position."""
    for d in meta.position_definitions or []:
        if d.name == position and d.top_objective_z_um is not None:
            return d.top_objective_z_um, d.bottom_objective_z_um
    # Older stores: one global value per objective, written as e.g. "347.1 um"
    top = float(meta.model_extra["Top Objective Stage"].split()[0])
    bottom = float(meta.model_extra["Bottom Objective Stage"].split()[0])
    return top, bottom


meta = load_daxi_metadata("/hpc/instruments/royer.vast.daxi2/Organelles/2026.04.15_Emma_peroxisome_5hr.ome.zarr")
for position in meta.timing_detail:  # every acquired position, in every spec version
    top, bottom = objective_z(meta, position)
    print(position, top - bottom, (top - bottom) / VERTICAL_UM_PER_ROW)
```

Run against two datasets on the cluster, this gives:

| Dataset | Position | top - bottom | Rows between top and bottom views |
|---|---|---|---|
| `2026.04.15_Emma_peroxisome_5hr` | pos0 | 75.7 um | about 580 (hand-verified: 600) |
| `2026.06.18_killifish_diapause_exit` | pos0 | 489.9 um | about 3,760 (more than the 2,368-row frame, so no overlap) |
| `2026.06.18_killifish_diapause_exit` | pos1 | 81.8 um | about 630 (not yet verified) |

## Room coordinate system

The stored arrays are `[T, C, Z, Y, X]`, but the stored axis names do not match the room. Stored **Z** is the stage scan
axis, which is horizontal in the room. The room's vertical axis is stored **Y**. This page calls the room axes
*scan*, *lateral* and *vertical* to avoid that clash.

| Room axis | Stored axis | What it is | Physical size per index |
|---|---|---|---|
| Scan (horizontal) | Z | Stage position during the sweep, from `x_start_mm` to `x_end_mm` | `z_step_size_um` (for example 1.018 um) |
| Vertical | Y | Camera rows. The objectives move along this axis | 0.1842 um along the sheet; about 0.13 um vertically (see below) |
| Lateral (horizontal) | X | Camera columns | 0.1842 um |

Two details matter when working in these coordinates:

- **Camera rows are oblique.** The light sheet is tilted, so each camera row lies partly along the scan axis and partly
  along the vertical. Raw volumes are therefore sheared; deskewing (for example in impp) removes the scan component
  and keeps Y in raw-row units. The vertical distance per row depends on the sheet angle, which is not recorded in the
  metadata.
- **Top and bottom views are mirrored in Y.** The two objectives face each other, so a structure near row 0 in a top
  view appears near the last row in the matching bottom view. Any comparison of top and bottom views must flip one of
  them in Y first. impp flips the bottom view.

### Views

Views are numbered from 1 in the metadata (`views`, `views_to_acquire`, `timing_detail`) and from 0 along the stored
C axis.

| Metadata view | Stored C index | Objective | Side | Channel label in the store |
|---|---|---|---|---|
| 1 | 0 | Bottom | A | `Bottom Objective, Side A \| v1_c1` |
| 2 | 1 | Bottom | B | `Bottom Objective, Side B \| v2_c1` |
| 3 | 2 | Top | A | `Top Objective, Side A \| v3_c1` |
| 4 | 3 | Top | B | `Top Objective, Side B \| v4_c1` |

## Position fields

An excerpt from a two-position acquisition (`timing_detail` and `camera_rois` trimmed):

```json
{
  "daxi": {
    "version": "0.2",
    "Top Objective Stage": "359.3 um",
    "Bottom Objective Stage": "-118.5 um",
    "objective_position_offset_um": 125.0,
    "estimated_volume_offset_um": 602.8,
    "z_scan_range_um": 1500,
    "z_step_size_um": 1.018,
    "views_to_acquire": [1, 2, 3, 4],
    "positions": {"pos0": [0.0, 0.0], "pos1": [0.0, 0.0]},
    "position_definitions": [
      {"name": "pos0", "x_start_mm": 0.0, "x_end_mm": 1.5, "y_start_mm": 0.0, "y_end_mm": 0.0,
       "scan_range_um": 1500.0, "views": [1, 2, 3, 4],
       "top_objective_z_um": 369.2, "bottom_objective_z_um": -120.7},
      {"name": "pos1", "x_start_mm": 0.0, "x_end_mm": 1.5, "y_start_mm": 0.0, "y_end_mm": 0.0,
       "scan_range_um": 1500.0, "views": [1, 2, 3, 4],
       "top_objective_z_um": 168.5, "bottom_objective_z_um": 86.7}
    ]
  }
}
```

| Field | Meaning | Reliability |
|---|---|---|
| `position_definitions[].top_objective_z_um`, `bottom_objective_z_um` | Objective positions for this position, in um, along the vertical axis | The source to use when present |
| `Top Objective Stage`, `Bottom Objective Stage` | One global value per objective, as a string with a unit (`"347.1 um"`) | Use only when `position_definitions` is absent. In multi-position stores it matches no single position |
| `position_definitions[].x_start_mm`, `x_end_mm` | Start and end of the stage sweep along the scan axis | `scan_range_um` equals `1000 * (x_end_mm - x_start_mm)`, and the stored Z length is about `scan_range_um / z_step_size_um` |
| `position_definitions[].y_start_mm`, `y_end_mm` | Stage position along the lateral axis | Recorded as 0 in the example above |
| `position_definitions[].views` | Views acquired at this position (1-based) | |
| `positions` | Legacy `{name: [x, y]}` in mm. Optional, and absent from some newer stores | Can be stale: the example records `[0, 0]` for positions whose sweep spans 0 to 1.5 mm. Prefer `position_definitions` |
| `objective_position_offset_um` | A per-acquisition constant written by Cyano | Meaning unknown; does not predict the top/bottom offset (below) |
| `estimated_volume_offset_um` | Cyano's estimate: `Top Objective Stage - Bottom Objective Stage + objective_position_offset_um` | The formula is exact in every store checked, but its value does not match a verified alignment (below) |
| `camera_rois` | Sensor region per camera serial, in pixels (`height` is rows, `width` is columns) | |

The objective positions are recorded once per position, not per timepoint, so sample drift over a time-lapse is not
captured.

## Converting objective positions to a vertical offset

### How the offset appears in the data

After one view is flipped in Y (see [Room coordinate system](#room-coordinate-system)), the top and bottom fields of
view differ by a vertical translation. impp stores that translation as `top_bottom_offsets: [oz, oy, ox]` in
`views_alignment.yaml`, in level-0 voxels, and places the Y-flipped bottom view at that offset from the top view. In
raw camera rows (level 0, frame height `H`, 2,368 rows on DaXi B) this means:

```
row_in_top_view + row_in_bottom_view = H - 1 - oy
```

so the centers of the two fields of view are `oy` rows apart vertically.

### Evidence for the rule

The Emma peroxisome dataset (`2026.04.15_Emma_peroxisome_5hr`) has a hand-verified alignment with `oy = 600` rows
(`top_bottom_offsets: [-5, 600, 16]`). Its objectives report top - bottom = 75.7 um and `objective_position_offset_um`
= 98. Converting 600 rows to um needs the vertical size of a row, so each candidate formula implies a row size:

| Candidate formula | Predicted offset | Vertical um per row needed for 600 rows | Plausible? |
|---|---|---|---|
| top - bottom | 75.7 um | 0.126 | Yes. Between the 45 degree value (0.130) and the value implied by impp's deskew shear (0.117) |
| top - bottom + offset (`estimated_volume_offset_um`) | 173.7 um | 0.290 | No. Larger than a camera pixel (0.1842 um) |
| \|top - bottom - offset\| | 22.3 um | 0.037 | No |

The killifish dataset (`2026.06.18_killifish_diapause_exit`) is consistent with the same rule: at pos0 the objectives
are 489.9 um apart, which predicts about 3,760 rows, more than the frame height. The top and bottom views there share
no visible structure.

### What the metadata cannot give you

The rule gives the offset between the top and bottom views. It does not give an absolute vertical coordinate for a
voxel: nothing in the metadata records which camera row sits at a given objective position, or which direction of
increasing row index points up.

## Pixel sizes and pyramid levels

Level 0 has a camera pixel of 0.1842 um and a Z step of `z_step_size_um`. Level 1 is downsampled 4x on Z, Y and X, so
each level-1 voxel is 4x larger. Stores written with `build_plate_spec` before this was fixed declare level-1 Z, Y and X
scales 4x smaller than level 0 instead (16x too small). Their level-1 scales are wrong, so compute them from the
level-0 scale.

## Open questions

- **Vertical size of a camera row.** The rule needs it to convert between um and rows. Candidates are 0.130 um (45
  degree sheet, used by earlier deskewed stores), 0.117 um (implied by the Z shear in impp's per-view deskew matrices
  with a 0.1842 um in-sheet pixel) and 0.1842 um (the scale impp writes on fused output). With 0.1842, the verified 600
  rows would be 110 um, and none of the formulas above would fit.
- **A second calibration.** One verified alignment cannot separate a slope from a constant. Killifish pos1 is a good
  test: the rule predicts about 630 to 700 rows.
- **Sign.** Whether increasing row index points up or down in the room is not recorded.
- **`objective_position_offset_um`.** Its meaning is unknown. It is not the objective separation at which the views
  coincide.

## Checking an alignment by eye

The scripts in `/hpc/mydata/seth.hinz/forensics/killifish_mip/` build a single self-contained HTML page per dataset
in which the top-view max projection can be dragged over the bottom-view one, with a live readout of the objective
positions, the current shift in rows and um, and the impp `oy` / `ox` that shift implies:

```bash
uv run --no-project --with 'zarr<3' --with tifffile --with numpy \
    python mips_series.py --root STORE.ome.zarr --step 10 --out OUTDIR
uv run --no-project --with tifffile --with numpy --with pillow \
    python build_viewer.py --root STORE.ome.zarr --mips OUTDIR --step 10 --tb-offsets -5 600 16
```
