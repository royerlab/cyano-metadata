"""
DaXi microscope metadata specifications.

This package contains metadata models for all versions of the DaXi microscope.
Import specific versions explicitly, or use the convenience imports for the current stable version.

Examples
--------
Import a specific version:
    >>> from cyano_metadata.daxi.v0_1 import DaxiMetadata

Import the current stable version (convenience):
    >>> from cyano_metadata.daxi import DaxiMetadata
"""

# Re-export current stable version for convenience
from .v0_1 import DaxiMetadata, PositionDefinition, TimingEntry

__all__ = ["DaxiMetadata", "PositionDefinition", "TimingEntry"]
