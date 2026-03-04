"""Tests for DaXi v0.2 metadata models (re-export of v0.1)."""

import json
from pathlib import Path

from cyano_metadata_specs.daxi.v0_2 import DaxiMetadata

SAMPLES_DIR = Path(__file__).parent.parent / "samples" / "daxi" / "v0_2"


def test_all_v0_2_samples_parse():
    """Ensure all v0.2 sample files parse without error."""
    sample_files = sorted(SAMPLES_DIR.glob("*.json"))
    assert len(sample_files) > 0, "No v0.2 sample files found"

    for sample_file in sample_files:
        with sample_file.open() as f:
            data = json.load(f)

        metadata = DaxiMetadata.model_validate(data)
        assert metadata.version == "0.2"


def test_v0_2_backward_compatibility():
    """Test that v0.2 models can read v0.1 data."""
    v0_1_samples_dir = Path(__file__).parent.parent / "samples" / "daxi" / "v0_1"
    sample_files = sorted(v0_1_samples_dir.glob("*.json"))

    for sample_file in sample_files:
        with sample_file.open() as f:
            data = json.load(f)

        metadata = DaxiMetadata.model_validate(data)
        assert metadata.version == "0.1"
