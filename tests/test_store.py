"""Tests for locating and loading a DaXi block out of a zarr store."""

import json

import pytest

from cyano_metadata.daxi.v0_3 import SUPPORTED_VERSIONS, DaxiMetadata, load_daxi_metadata
from cyano_metadata.errors import InvalidDaxiBlockError, UnsupportedDaxiVersionError
from cyano_metadata.store import find_attrs_block, read_group_attributes

# A minimal but valid v0.3 block. Kept inline so the tests do not depend on the
# sample files, which are fixtures for the model rather than for the store.
VALID_BLOCK = {
    "version": "0.3",
    "microscope_name": "Daxi B",
    "framerate_hz": 60,
    "global_exposure_ms": 8.47,
    "positions": {"pos0": [0.0, 0.0]},
    "timing_detail": {"pos0": {"0": {"1": {"start": 1.0, "end": 2.0}}}},
    "processing": {
        "780nm": {"subtract": None, "quantize_step": 4},
        "488nm": {"subtract": 100, "quantize_step": None},
    },
}


def write_v2_group(directory, attrs):
    """Write zarr v2 group attributes and return the group directory."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / ".zattrs").write_text(json.dumps(attrs))
    return directory


def write_v3_group(directory, attrs):
    """Write zarr v3 group metadata and return the group directory."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "zarr.json").write_text(json.dumps({"zarr_format": 3, "attributes": attrs}))
    return directory


class TestReadGroupAttributes:
    def test_reads_zarr_v2_zattrs(self, tmp_path):
        write_v2_group(tmp_path / "group", {"daxi": {"version": "0.3"}})
        assert read_group_attributes(tmp_path / "group") == {"daxi": {"version": "0.3"}}

    def test_reads_zarr_v3_attributes(self, tmp_path):
        write_v3_group(tmp_path / "group", {"daxi": {"version": "0.3"}})
        assert read_group_attributes(tmp_path / "group") == {"daxi": {"version": "0.3"}}

    def test_prefers_zattrs_when_both_present(self, tmp_path):
        group = write_v2_group(tmp_path / "group", {"which": "v2"})
        write_v3_group(group, {"which": "v3"})
        assert read_group_attributes(group) == {"which": "v2"}

    @pytest.mark.parametrize("content", ["not json at all", '["a", "list"]'])
    def test_unreadable_or_non_object_content_is_empty(self, tmp_path, content):
        """Callers sweep many candidate paths, so junk must not raise."""
        group = tmp_path / "group"
        group.mkdir()
        (group / ".zattrs").write_text(content)
        assert read_group_attributes(group) == {}

    def test_missing_group_is_empty(self, tmp_path):
        assert read_group_attributes(tmp_path / "absent") == {}


class TestFindAttrsBlock:
    @pytest.mark.parametrize("depth", [0, 1, 2, 3])
    def test_walks_up_to_the_default_depth(self, tmp_path, depth):
        """A position four levels deep still reaches a plate-root block."""
        root = write_v2_group(tmp_path / "plate", {"daxi": VALID_BLOCK})
        deep = root.joinpath(*[f"level{i}" for i in range(depth)])
        deep.mkdir(parents=True, exist_ok=True)

        block, found_at = find_attrs_block(deep)
        assert block == VALID_BLOCK
        assert found_at == root

    def test_does_not_walk_past_the_limit(self, tmp_path):
        root = write_v2_group(tmp_path / "plate", {"daxi": VALID_BLOCK})
        too_deep = root / "a" / "b" / "c" / "d"
        too_deep.mkdir(parents=True)
        assert find_attrs_block(too_deep) == (None, None)

    def test_nearest_group_wins_over_ancestor(self, tmp_path):
        """A block written directly onto a group overrides an inherited one."""
        root = write_v2_group(tmp_path / "plate", {"daxi": {"version": "0.1"}})
        child = write_v2_group(root / "child", {"daxi": {"version": "0.3"}})

        block, found_at = find_attrs_block(child)
        assert block == {"version": "0.3"}
        assert found_at == child

    def test_absent_key(self, tmp_path):
        group = write_v2_group(tmp_path / "plate", {"multiscales": [], "omero": {}})
        assert find_attrs_block(group) == (None, None)

    def test_non_dict_block_is_ignored(self, tmp_path):
        group = write_v2_group(tmp_path / "plate", {"daxi": "not a mapping"})
        assert find_attrs_block(group) == (None, None)

    def test_key_is_configurable(self, tmp_path):
        group = write_v2_group(tmp_path / "plate", {"plate": {"version": "0.4"}})
        block, _ = find_attrs_block(group, key="plate")
        assert block == {"version": "0.4"}


class TestLoadDaxiMetadata:
    def test_absent_block_returns_none(self, tmp_path):
        """Absence is a normal state, not an error."""
        group = write_v2_group(tmp_path / "plate", {"multiscales": []})
        assert load_daxi_metadata(group) is None

    def test_loads_from_a_descendant_group(self, tmp_path):
        root = write_v2_group(tmp_path / "plate", {"daxi": VALID_BLOCK})
        position = root / "22500103" / "488nm" / "pos0"
        position.mkdir(parents=True)

        metadata = load_daxi_metadata(position)
        assert isinstance(metadata, DaxiMetadata)
        assert metadata.processing is not None
        record = metadata.processing.for_label("488nm")
        assert record is not None
        assert record.subtracted == 100

    def test_loads_zarr_v3_store(self, tmp_path):
        group = write_v3_group(tmp_path / "plate", {"daxi": VALID_BLOCK})
        metadata = load_daxi_metadata(group)
        assert metadata is not None
        assert metadata.version == "0.3"

    @pytest.mark.parametrize("version", sorted(SUPPORTED_VERSIONS))
    def test_reads_every_supported_version(self, tmp_path, version):
        block = {**VALID_BLOCK, "version": version}
        group = write_v2_group(tmp_path / version, {"daxi": block})
        metadata = load_daxi_metadata(group)
        assert metadata is not None
        assert metadata.version == version

    def test_unsupported_version_raises_and_names_the_fix(self, tmp_path):
        block = {**VALID_BLOCK, "version": "0.9"}
        group = write_v2_group(tmp_path / "plate", {"daxi": block})

        with pytest.raises(UnsupportedDaxiVersionError) as caught:
            load_daxi_metadata(group)
        assert caught.value.version == "0.9"
        assert "upgrade cyano-metadata" in str(caught.value)

    def test_unsupported_version_wins_over_field_errors(self, tmp_path):
        """A future spec's new fields should not mask the real problem."""
        block = {**VALID_BLOCK, "version": "0.9", "processing": {"488nm": {"clip_high": 5}}}
        group = write_v2_group(tmp_path / "plate", {"daxi": block})

        with pytest.raises(UnsupportedDaxiVersionError):
            load_daxi_metadata(group)

    def test_unknown_processing_op_is_invalid(self, tmp_path):
        """The processing vocabulary is closed, so a new op must not be dropped."""
        block = {**VALID_BLOCK, "processing": {"488nm": {"clip_high": 5}}}
        group = write_v2_group(tmp_path / "plate", {"daxi": block})

        with pytest.raises(InvalidDaxiBlockError) as caught:
            load_daxi_metadata(group)
        assert caught.value.path == group

    def test_missing_required_field_is_invalid(self, tmp_path):
        block = {k: v for k, v in VALID_BLOCK.items() if k != "positions"}
        group = write_v2_group(tmp_path / "plate", {"daxi": block})

        with pytest.raises(InvalidDaxiBlockError):
            load_daxi_metadata(group)

    def test_negative_subtract_is_invalid(self, tmp_path):
        """A negative pedestal would invert the sign of any compensation."""
        block = {**VALID_BLOCK, "processing": {"488nm": {"subtract": -5}}}
        group = write_v2_group(tmp_path / "plate", {"daxi": block})

        with pytest.raises(InvalidDaxiBlockError):
            load_daxi_metadata(group)
