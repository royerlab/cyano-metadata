"""Supporting models for DaXi metadata v0.1/v0.2."""

from pydantic import BaseModel, Field


class TimingEntry(BaseModel):
    """Timing information for a single view acquisition."""

    start: float = Field(..., description="Start timestamp (Unix time)")
    end: float = Field(..., description="End timestamp (Unix time)")


class PositionDefinition(BaseModel):
    """
    Extended position definition with per-position scan parameters.

    This is a future field not yet present in v0.1/v0.2 data but defined in the acquisition code.
    """

    name: str = Field(..., description="Position identifier (e.g., 'pos0')")
    x_start_mm: float = Field(..., description="X start coordinate in mm")
    y_start_mm: float = Field(..., description="Y start coordinate in mm")
    x_end_mm: float = Field(..., description="X end coordinate in mm")
    y_end_mm: float = Field(..., description="Y end coordinate in mm")
    scan_range_um: float = Field(..., description="Z scan range in microns")
    views: list[int] = Field(..., description="Views to acquire for this position")
    top_objective_z_um: float | None = Field(None, description="Top objective Z position in microns")
    bottom_objective_z_um: float | None = Field(None, description="Bottom objective Z position in microns")
