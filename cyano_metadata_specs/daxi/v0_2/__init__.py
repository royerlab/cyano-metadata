"""
DaXi metadata specification version 0.2.

Due to the messy initial drafting process, v0.1 and v0.2 datasets are not strictly
compliant to either spec. This version re-exports the v0.1 models which are designed
to handle both v0.1 and v0.2 data with full backward compatibility.

For implementation details, see cyano_metadata_specs.daxi.v0_1.
"""

from ..v0_1 import DaxiMetadata, PositionDefinition, TimingEntry

__all__ = ["DaxiMetadata", "PositionDefinition", "TimingEntry"]
