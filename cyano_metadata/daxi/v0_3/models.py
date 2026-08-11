"""Supporting models for DaXi metadata v0.3.

v0.3 introduces the ``processing`` record: a per-wavelength log of the
value-level operations (background subtraction, quantization) applied to a
stored dataset, if any. It is keyed by channel wavelength because a camera can
carry more than one wavelength, so the wavelength is the stable unique key.
"""

from pydantic import BaseModel, ConfigDict, Field, RootModel


class ChannelProcessing(BaseModel):
    """Lossy, value-level processing applied to one wavelength/channel.

    A closed, intentionally tiny vocabulary: only simple value-level operations
    belong here. Anything spatial (fusion, deskew, registration, stitching) is
    out of scope and must not be recorded here. Encountering an unknown key is an
    error, not something to silently ignore: a new operation means a new spec
    version.
    """

    model_config = ConfigDict(extra="forbid")

    subtract: int | None = Field(
        None,
        description=(
            "Background floor removed as max(x - N, 0); null if not subtracted. "
            "Downstream code must not subtract the pedestal again."
        ),
    )
    quantize_step: int | None = Field(
        None,
        description="Values rounded to the nearest multiple of N; null if not quantized.",
    )


class Processing(RootModel[dict[str, ChannelProcessing]]):
    """Per-wavelength processing map, keyed by channel wavelength (e.g. ``"561nm"``).

    A lossy copy writes this under ``.zattrs["daxi"]["processing"]`` so the
    recompressed dataset is self-identifying per channel: each wavelength records
    independently whether it was subtracted and/or quantized. Label-free channels
    typically have ``subtract`` null; fluorophore channels typically carry a
    subtract and may or may not be quantized.
    """

    root: dict[str, ChannelProcessing]
