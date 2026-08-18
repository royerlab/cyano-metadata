"""Supporting models for DaXi metadata v0.3.

v0.3 introduces the ``processing`` record: a per-wavelength log of the
value-level operations (background subtraction, quantization) applied to a
stored dataset, if any. It is keyed by channel wavelength because a camera can
carry more than one wavelength, so the wavelength is the stable unique key.

Wavelength keys are opaque strings and are never parsed into numbers. The digits
in ``"488nm"`` are a naming convention, not an identifier scheme: a
supercontinuum or white-light channel is legitimately keyed ``"supercontinuum"``
or ``"white"``. Consumers match key to key, which works because the same strings
become the HCS column names of the store.
"""

from pydantic import BaseModel, ConfigDict, Field, RootModel

from ...errors import AmbiguousWavelengthError


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
        ge=0,
        description=(
            "Background floor removed as max(x - N, 0); null if not subtracted. "
            "Downstream code must not subtract the pedestal again."
        ),
    )
    quantize_step: int | None = Field(
        None,
        description="Values rounded to the nearest multiple of N; null if not quantized.",
    )

    @property
    def subtracted(self) -> int:
        """Counts removed from this channel, as a number rather than an option.

        ``null`` and ``0`` both mean nothing was removed, so a consumer deciding
        how much to compensate for never has to special-case the absent value.
        """
        return self.subtract or 0


class Processing(RootModel[dict[str, ChannelProcessing]]):
    """Per-wavelength processing map, keyed by channel wavelength (e.g. ``"561nm"``).

    A lossy copy writes this under ``.zattrs["daxi"]["processing"]`` so the
    recompressed dataset is self-identifying per channel: each wavelength records
    independently whether it was subtracted and/or quantized. Label-free channels
    typically have ``subtract`` null; fluorophore channels typically carry a
    subtract and may or may not be quantized.
    """

    root: dict[str, ChannelProcessing]

    def labels(self) -> set[str]:
        """The wavelength keys exactly as written, e.g. ``{"488nm", "780nm"}``."""
        return set(self.root)

    def for_label(self, label: str) -> ChannelProcessing | None:
        """Return the record for one wavelength key, or None if it is absent.

        Matches the key exactly first, then retries ignoring case and surrounding
        whitespace so that ``"488 nm"`` still finds ``"488nm"``. That is the only
        tolerance: the key is never decomposed into a number and a unit.

        Parameters
        ----------
        label:
            Wavelength key to look up.

        Returns
        -------
        ChannelProcessing or None
            The record, or None when no key matches.

        Raises
        ------
        AmbiguousWavelengthError
            If *label* loosely matches more than one key, which makes the record
            ambiguous and unsafe to guess at.
        """
        exact = self.root.get(label)
        if exact is not None:
            return exact

        wanted = _loose(label)
        matches = [key for key in self.root if _loose(key) == wanted]
        if len(matches) > 1:
            raise AmbiguousWavelengthError(label, matches)
        return self.root[matches[0]] if matches else None


def _loose(label: str) -> str:
    """Normalize a wavelength key for tolerant comparison, without parsing it."""
    return "".join(label.split()).casefold()
