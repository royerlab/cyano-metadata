"""Locate a metadata block inside an OME-Zarr store.

This package owns the ``daxi`` key within an OME-Zarr store, so finding that
key is its job: the alternative is every consumer reimplementing the same
``.zattrs`` walk. Nothing here validates or imports a model, and nothing here
needs a zarr dependency -- group attributes are plain JSON on disk.

The walk exists because a DaXi acquisition writes its block only at the plate
root. Per-position groups carry just ``multiscales`` and ``omero``, so a caller
holding a position path has to look upwards to find it.
"""

from __future__ import annotations

import json
from pathlib import Path

__all__ = ["find_attrs_block", "read_group_attributes"]

#: Zarr v2 keeps group attributes in their own file.
_ZARR_V2_ATTRS = ".zattrs"

#: Zarr v3 inlines them under an ``attributes`` key.
_ZARR_V3_METADATA = "zarr.json"


def read_group_attributes(group_path: Path | str) -> dict:
    """Return the attributes of one zarr group.

    Reads ``.zattrs`` (zarr v2) and falls back to the ``attributes`` member of
    ``zarr.json`` (zarr v3). A group with no attributes, or a path that is not a
    zarr group at all, yields an empty dict rather than an error -- callers walk
    over many candidate paths and absence is expected.

    Parameters
    ----------
    group_path:
        Directory of the zarr group.

    Returns
    -------
    dict
        The group's attributes, or ``{}``.
    """
    group_path = Path(group_path)

    v2 = group_path / _ZARR_V2_ATTRS
    if v2.is_file():
        return _read_json_object(v2)

    v3 = group_path / _ZARR_V3_METADATA
    if v3.is_file():
        attributes = _read_json_object(v3).get("attributes", {})
        return attributes if isinstance(attributes, dict) else {}

    return {}


def find_attrs_block(
    path: Path | str,
    key: str = "daxi",
    max_levels: int = 3,
) -> tuple[dict | None, Path | None]:
    """Find the named attributes block on *path* or its nearest ancestor.

    Searches *path* itself first, then walks upwards. The first group carrying
    *key* wins, so a block written directly onto a position takes precedence
    over one inherited from the plate root.

    The default depth of three covers a full DaXi layout: a position at
    ``<plate>/<camera>/<wavelength>/<position>`` reaches the plate root.

    Parameters
    ----------
    path:
        Zarr group to start from.
    key:
        Attribute key to look for.
    max_levels:
        How many ancestor levels to search beyond *path* itself.

    Returns
    -------
    tuple
        ``(block, group_path)`` for the first hit, or ``(None, None)``.
    """
    path = Path(path)

    for candidate in [path, *path.parents[:max_levels]]:
        block = read_group_attributes(candidate).get(key)
        if isinstance(block, dict):
            return block, candidate

    return None, None


def _read_json_object(json_path: Path) -> dict:
    """Load a JSON object, treating unreadable or non-object content as empty."""
    try:
        with json_path.open(encoding="utf-8") as handle:
            loaded = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}
