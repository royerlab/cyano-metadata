"""DaXi-specific HCS plate layout specification.

This module provides Pydantic models and a builder function that encode the Cyano
convention for mapping DaXi acquisition parameters onto an OME-Zarr HCS plate:

    row    = camera identifier (alphanumeric serial number)
    column = wavelength label  (e.g. "488nm")
    well   = position name     (e.g. "pos0")

The builder computes per-position scale transforms (T, V, Z, Y, X) for both
full-resolution and 4x-downsampled pyramid levels.

The output ``PlateSpec`` is a lightweight recipe consumed by
``cyano_streams.create_hcs_layout()`` to make the actual iohub calls — this
module has no iohub dependency.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# View naming (mirrors daxi2/daxi/widgets/view_flipper.py)
# ---------------------------------------------------------------------------
_OBJECTIVE_NAMES = ["Bottom Objective", "Top Objective"]
_SIDE_NAMES = ["Side A", "Side B"]

DOWNSAMPLE_FACTOR = 4


def _view_display_name(view: int) -> str:
    """Human-readable name for a DaXi view index (1-based)."""
    idx = view - 1
    obj = idx // len(_SIDE_NAMES)
    side = idx % len(_SIDE_NAMES)
    return f"{_OBJECTIVE_NAMES[obj]}, {_SIDE_NAMES[side]}"


# ---------------------------------------------------------------------------
# Input models — what the caller provides
# ---------------------------------------------------------------------------
class CameraSpec(BaseModel):
    """Description of a single camera for plate layout construction."""

    serial_number: str = Field(..., description="Camera serial number")
    wavelengths: list[int] = Field(..., description="Laser wavelengths this camera captures (nm)")
    pixel_size_um: float = Field(..., description="Camera pixel size in micrometers")


class AcqPositionSpec(BaseModel):
    """Description of a single acquisition position."""

    name: str = Field(..., description="Position identifier (e.g. 'pos0')")
    scan_range_um: float = Field(..., description="Z scan range for this position in micrometers")
    views: list[int] | None = Field(
        None,
        description="Per-position view indices (1-based). Falls back to global_views if None.",
    )


# ---------------------------------------------------------------------------
# Output models — the plate recipe
# ---------------------------------------------------------------------------
class PositionDescriptor(BaseModel):
    """One position-channel node to create in the HCS plate.

    Maps directly to one ``plate.create_position(row, column, well)`` call
    followed by ``_create_image_meta`` for each resolution level.
    """

    row: str = Field(..., description="HCS row — camera identifier (alphanumeric)")
    column: str = Field(..., description="HCS column — wavelength label (e.g. '488nm')")
    well: str = Field(..., description="HCS well — position name (e.g. 'pos0')")
    scales: dict[str, list[float]] = Field(
        ...,
        description=(
            "Resolution level name → [T, V, Z, Y, X] scale transform. "
            "Level '0' is full resolution, '1' is 4x downsampled."
        ),
    )


class PlateSpec(BaseModel):
    """Declarative description of an HCS plate layout.

    This is not an HCS model — iohub owns those. It is a recipe that tells
    ``cyano_streams.create_hcs_layout()`` what iohub calls to make.
    """

    channel_names: list[str] = Field(
        ..., description="Plate-level channel names for iohub (one per unique view)"
    )
    positions: list[PositionDescriptor] = Field(
        ..., description="Position-channel nodes to create"
    )


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------
def build_plate_spec(
    cameras: list[CameraSpec],
    positions: list[AcqPositionSpec],
    frame_rate_hz: float,
    z_step_size_um: float,
    global_views: list[int],
) -> PlateSpec:
    """Construct a ``PlateSpec`` from DaXi acquisition parameters.

    Encodes the Cyano convention (row=camera, column=wavelength, well=position)
    and computes per-position scale transforms for full-resolution and
    4x-downsampled pyramid levels.

    Parameters
    ----------
    cameras:
        Camera descriptions. Each camera's ``wavelengths`` list determines
        which HCS columns it contributes.
    positions:
        Acquisition positions. Per-position ``views`` override *global_views*
        when set.
    frame_rate_hz:
        Camera frame rate in Hz (shared across all cameras).
    z_step_size_um:
        Global Z step size in micrometers. The actual per-position Z step is
        adjusted so that z_planes evenly divides the scan range.
    global_views:
        Default view indices (1-based) used when a position doesn't specify its own.
    """
    # Collect all unique views across all positions for plate-level channel names
    all_views: set[int] = set()
    for pos in positions:
        pos_views = pos.views if pos.views is not None else global_views
        all_views.update(pos_views)
    all_views_sorted = sorted(all_views)

    channel_names = [
        f"{_view_display_name(v)} | v{v}_c1" for v in all_views_sorted
    ]

    # Build wavelength → camera lookup
    wl_to_camera: dict[int, CameraSpec] = {}
    for cam in cameras:
        for wl in cam.wavelengths:
            wl_to_camera[wl] = cam

    # Build position descriptors
    descriptors: list[PositionDescriptor] = []

    for pos in positions:
        pos_views = pos.views if pos.views is not None else global_views

        # Per-position Z geometry
        z_planes = int(pos.scan_range_um / z_step_size_um)
        if z_planes <= 0:
            z_planes = 1
        pos_z_step = pos.scan_range_um / z_planes

        # Per-position timepoint duration
        volume_sweep_s = z_planes / frame_rate_hz
        timepoint_duration_s = volume_sweep_s * len(pos_views)

        for cam in cameras:
            camera_name = "".join(ch for ch in cam.serial_number if ch.isalnum())

            for wl in sorted(cam.wavelengths):
                channel_label = f"{wl}nm"

                full_scale = [
                    timepoint_duration_s,
                    1.0,  # views are unitless
                    pos_z_step,
                    cam.pixel_size_um,
                    cam.pixel_size_um,
                ]
                downsampled_scale = full_scale[:2] + [
                    s / DOWNSAMPLE_FACTOR for s in full_scale[2:]
                ]

                descriptors.append(
                    PositionDescriptor(
                        row=camera_name,
                        column=channel_label,
                        well=pos.name,
                        scales={
                            "0": full_scale,
                            "1": downsampled_scale,
                        },
                    )
                )

    return PlateSpec(channel_names=channel_names, positions=descriptors)
