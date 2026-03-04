"""DaXi metadata model for versions 0.1 and 0.2.

Due to the messy initial drafting process, v0.1 and v0.2 datasets are not strictly compliant
to either spec. This model is designed to handle both versions with backward compatibility.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .models import PositionDefinition, TimingEntry


class DaxiMetadata(BaseModel):
    """
    Metadata model for DaXi microscope acquisitions.

    Handles both v0.1 and v0.2 metadata formats. All fields introduced in v0.2 are optional
    to maintain backward compatibility with v0.1 data.

    The timing_detail structure is:
    {
        "pos0": {
            "0": {  # timepoint
                "1": {"start": ..., "end": ...},  # view
                "2": {"start": ..., "end": ...}
            }
        }
    }

    The positions structure (legacy format) is:
    {
        "pos0": [x, y],  # Coordinates in mm
        "pos1": [x, y]
    }
    """

    model_config = ConfigDict(extra="allow")  # Allow KCube stage positions and other dynamic fields

    version: str = Field(..., description="Metadata version (e.g., '0.1', '0.2')")
    microscope_name: str = Field(..., description="Name of the microscope")
    framerate_hz: int | float = Field(..., description="Frame rate in Hz")
    global_exposure_ms: float = Field(..., description="Global exposure time in milliseconds")

    # Position definitions (legacy format: dict mapping position names to [x, y] coordinates)
    positions: dict[str, tuple[float, float]] = Field(
        ..., description="Position definitions as dict mapping position name to [x, y] coordinates"
    )

    # Timing information (nested structure: position -> timepoint -> view -> {start, end})
    timing_detail: dict[str, dict[str, dict[str, TimingEntry]]] = Field(
        ..., description="Nested timing information for each position, timepoint, and view"
    )

    # V0.2 fields (all optional for backward compatibility)
    views_to_acquire: list[int] | None = Field(None, description="List of view indices to acquire (v0.2+)")
    z_scan_range_um: float | None = Field(None, description="Z scan range in microns (v0.2+)")
    z_step_size_um: float | None = Field(None, description="Z step size in microns (v0.2+)")
    objective_position_offset_um: float | None = Field(
        None, description="Objective position offset in microns (v0.2+)"
    )
    estimated_volume_offset_um: float | None = Field(
        None, description="Estimated volume offset in microns (v0.2+)"
    )

    # Future field (not yet in actual data but defined in acquisition code)
    position_definitions: list[PositionDefinition] | None = Field(
        None, description="Extended position definitions with per-position parameters (future)"
    )

    def __getattr__(self, name: str) -> Any:
        """
        Allow access to extra fields (e.g., KCube stage positions) as attributes.

        This enables accessing dynamic fields like metadata.Top_Objective_Stage
        without raising AttributeError.
        """
        if name in self.model_extra:  # type: ignore[attr-defined]
            return self.model_extra[name]  # type: ignore[attr-defined]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
