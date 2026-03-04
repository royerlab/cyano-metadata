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
