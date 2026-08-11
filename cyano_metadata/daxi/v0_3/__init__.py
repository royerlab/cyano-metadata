"""DaXi metadata specification version 0.3.

v0.3 extends v0.2 with an optional per-wavelength ``processing`` record that
documents lossy, value-level operations (background subtract, quantization)
applied by a recompressed copy or by the scope itself when appropriate.
The plate builder is re-exported from v0.2 unchanged.
"""

from ..v0_1 import PositionDefinition, TimingEntry
from ..v0_2 import (
    AcqPositionSpec,
    CameraSpec,
    PlateSpec,
    PositionDescriptor,
    build_plate_spec,
)
from .metadata import DaxiMetadata
from .models import ChannelProcessing, Processing

__all__ = [
    "AcqPositionSpec",
    "CameraSpec",
    "ChannelProcessing",
    "DaxiMetadata",
    "PlateSpec",
    "PositionDefinition",
    "PositionDescriptor",
    "Processing",
    "TimingEntry",
    "build_plate_spec",
]
