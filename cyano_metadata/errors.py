"""Exception types raised when metadata is present but not interpretable.

These are deliberately narrow. They mean "a block is there and we cannot tell
what it says", never "the block is missing": absence is a normal state that
callers handle with a ``None`` return, not an exception.

Each condition carries its own class so the message lives with the error rather
than at the raise site, and so callers can catch a specific failure without
matching on message text.
"""

from pathlib import Path

__all__ = [
    "AmbiguousWavelengthError",
    "CyanoMetadataError",
    "DaxiMetadataError",
    "InvalidDaxiBlockError",
    "UnsupportedDaxiVersionError",
]


class CyanoMetadataError(ValueError):
    """Base class for metadata that is present but not interpretable."""


class DaxiMetadataError(CyanoMetadataError):
    """A DaXi metadata block is present but malformed, ambiguous, or unsupported."""


class AmbiguousWavelengthError(DaxiMetadataError):
    """A wavelength key loosely matches more than one entry in a processing map."""

    def __init__(self, label: str, matches: list[str]) -> None:
        self.label = label
        self.matches = sorted(matches)
        super().__init__(f"wavelength {label!r} matches more than one processing key: {self.matches}")


class InvalidDaxiBlockError(DaxiMetadataError):
    """A ``daxi`` block was found but does not conform to the spec."""

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"invalid daxi metadata at {path}: {reason}")


class UnsupportedDaxiVersionError(DaxiMetadataError):
    """A ``daxi`` block declares a spec version this package does not cover."""

    def __init__(self, version: str, supported: set[str]) -> None:
        self.version = version
        self.supported = sorted(supported)
        super().__init__(
            f"daxi metadata declares version {version!r}, which this package does not cover "
            f"(supported: {self.supported}); upgrade cyano-metadata"
        )
