"""Supporting models for DaXi metadata v0.3.

v0.3 introduces the ``processing`` record: a deliberately minimal log of the
background subtraction and quantization applied (if done at all).
"""

from pydantic import BaseModel, ConfigDict, Field


class FluorescenceClip(BaseModel):
    """Record that the fluorophore channels were clipped below a floor.

    The presence of this record means every fluorophore-channel value below
    ``min`` was clipped up to ``min`` (a background/pedestal floor). Downstream
    code must not subtract the pedestal again.
    """

    min: int = Field(..., description="Clip floor: fluorophore values below this were raised to it")


class Processing(BaseModel):
    """Lossy, post-camera processing applied to a stored DaXi dataset.

    A lossy copy writes this under ``.zattrs["daxi"]["processing"]`` so the
    recompressed dataset is self-identifying and downstream code cannot
    double-subtract or misquantify.

    This is a closed, intentionally tiny vocabulary — only simple value-level
    operations belong here. Anything spatial (fusion, deskew, registration,
    stitching) is out of scope and must not be recorded here. Encountering an
    unknown key is an error, not something to silently ignore: a new operation
    means a new spec version.
    """

    model_config = ConfigDict(extra="forbid")

    fluorescence_clip: FluorescenceClip | None = Field(
        None,
        description="Present iff the fluorophore channels were clipped below a floor",
    )
    quantize_step: int | None = Field(
        None,
        description="Present iff values were rounded to this multiple",
    )
