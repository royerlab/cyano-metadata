"""Tests for DaXi v0.2 metadata models (re-export of v0.1)."""

import json

from cyano_metadata.daxi.v0_2 import DaxiMetadata


def test_all_v0_2_samples_parse(daxi_v0_2_samples):
    """Ensure all v0.2 sample files parse without error."""
    sample_files = sorted(daxi_v0_2_samples.glob("*.json"))
    assert len(sample_files) > 0, "No v0.2 sample files found"

    for sample_file in sample_files:
        with sample_file.open() as f:
            data = json.load(f)

        metadata = DaxiMetadata.model_validate(data)
        assert metadata.version == "0.2"


def test_v0_2_backward_compatibility(daxi_v0_1_samples):
    """Test that v0.2 models can read v0.1 data."""
    sample_files = sorted(daxi_v0_1_samples.glob("*.json"))

    for sample_file in sample_files:
        with sample_file.open() as f:
            data = json.load(f)

        metadata = DaxiMetadata.model_validate(data)
        assert metadata.version == "0.1"


def test_positions_optional_with_position_definitions():
    """A block with only ``position_definitions`` is valid; legacy ``positions`` defaults to None."""
    metadata = DaxiMetadata.model_validate({
        "version": "0.2",
        "microscope_name": "Daxi B",
        "framerate_hz": 20,
        "global_exposure_ms": 41.8,
        "timing_detail": {},
        "position_definitions": [
            {
                "name": "pos0",
                "x_start_mm": 0.0,
                "x_end_mm": 1.3,
                "y_start_mm": 0.0,
                "y_end_mm": 0.0,
                "scan_range_um": 1300,
                "views": [1, 2, 3, 4],
            }
        ],
    })
    assert metadata.positions is None
    assert metadata.position_definitions is not None
    assert metadata.position_definitions[0].name == "pos0"
