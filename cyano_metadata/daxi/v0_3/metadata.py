"""DaXi metadata model for version 0.3.

v0.3 is v0.2 plus an optional ``processing`` record: a per-wavelength map of the
lossy, value-level operations (background subtract, quantization) done during
recompression (or on-scope). Every field from v0.1/v0.2 is inherited unchanged,
so v0.3 reads older data too; the new ``processing`` field is optional and
absent on freshly acquired datasets.
"""

from pydantic import Field

from ..v0_1.metadata import DaxiMetadata as DaxiMetadataV0_2
from .models import Processing


class DaxiMetadata(DaxiMetadataV0_2):
    """
    Metadata model for DaXi microscope acquisitions (v0.3).

    Extends the v0.1/v0.2 model with a per-wavelength ``processing`` record. A
    raw acquisition has no ``processing`` key; only a lossy copy writes one,
    recording per channel what it did so the clipped / quantized dataset is
    self-identifying.
    """

    processing: Processing | None = Field(
        None,
        description="Per-wavelength lossy processing applied by a recompression step or the scope (v0.3+)",
    )
