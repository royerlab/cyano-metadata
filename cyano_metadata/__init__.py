"""
Cyano metadata specifications.

Pydantic models and specs for Cyano-controlled microscope metadata.
This package contains adapters for all versions of microscope metadata and acts as a living specification.

Supported Microscopes
---------------------
- DaXi: Light-sheet microscope with multiple views
- QuadraVision: (future support)

Usage
-----
Import specific versions explicitly:
    >>> from cyano_metadata.daxi.v0_1 import DaxiMetadata
    >>> from cyano_metadata.daxi.v0_2 import DaxiMetadata

Or use the convenience imports for the current stable version:
    >>> from cyano_metadata.daxi import DaxiMetadata
"""

__version__ = "0.0.1"
