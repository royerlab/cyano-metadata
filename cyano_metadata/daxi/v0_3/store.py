"""Read a DaXi metadata block out of an OME-Zarr store and validate it as v0.3.

Because the v0.3 model inherits every v0.1/v0.2 field, this loader reads all
three spec versions. It reports problems by raising: whether a malformed block
should abort a pipeline or merely warn is an operational policy that belongs to
the consumer, not to the spec.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from ...errors import InvalidDaxiBlockError, UnsupportedDaxiVersionError
from ...store import find_attrs_block
from .metadata import DaxiMetadata

__all__ = ["DAXI_ATTR_KEY", "SUPPORTED_VERSIONS", "load_daxi_metadata"]

#: Spec versions this model can read. v0.3 inherits v0.1/v0.2 unchanged.
SUPPORTED_VERSIONS = frozenset({"0.1", "0.2", "0.3"})

#: Attribute key this package owns.
DAXI_ATTR_KEY = "daxi"


def load_daxi_metadata(path: Path | str) -> DaxiMetadata | None:
    """Return the validated DaXi metadata for *path*, or None if there is none.

    Looks for the ``daxi`` block on *path* and then on its ancestors, since an
    acquisition writes it only at the plate root.

    Parameters
    ----------
    path:
        Zarr group to read from: a plate root, or any group beneath one.

    Returns
    -------
    DaxiMetadata or None
        The validated metadata, or None when no ``daxi`` block exists. Absence is
        normal for stores written by other tools.

    Raises
    ------
    UnsupportedDaxiVersionError
        The block declares a spec version newer than this package covers.
    InvalidDaxiBlockError
        A block is present but does not conform to the spec.
    """
    block, group_path = find_attrs_block(Path(path), key=DAXI_ATTR_KEY)
    if block is None or group_path is None:
        return None

    # Checked before validation so that a future spec version reports the
    # actionable "upgrade cyano-metadata" rather than a field-level complaint
    # about whatever new key it introduced.
    version = block.get("version")
    if isinstance(version, str) and version not in SUPPORTED_VERSIONS:
        raise UnsupportedDaxiVersionError(version, set(SUPPORTED_VERSIONS))

    try:
        return DaxiMetadata.model_validate(block)
    except ValidationError as error:
        raise InvalidDaxiBlockError(group_path, str(error)) from error
